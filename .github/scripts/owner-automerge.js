"use strict";

const STATE_QUERY = `query OwnerAutoMergeState($id: ID!) {
  node(id: $id) {
    ... on PullRequest {
      autoMergeRequest { enabledAt mergeMethod }
      mergeStateStatus
      headRefOid
      isDraft
      author { login }
      headRepository { nameWithOwner }
      baseRepository { nameWithOwner }
      labels(first: 100) {
        nodes { name }
        pageInfo { hasNextPage }
      }
    }
  }
}`;

const ENABLE_MUTATION = `mutation EnableOwnerAutoMerge($id: ID!, $headOid: GitObjectID!) {
  enablePullRequestAutoMerge(input: {
    pullRequestId: $id,
    mergeMethod: SQUASH,
    expectedHeadOid: $headOid
  }) { clientMutationId }
}`;

const DISABLE_MUTATION = `mutation DisableOwnerAutoMerge($id: ID!) {
  disablePullRequestAutoMerge(input: { pullRequestId: $id }) { clientMutationId }
}`;

const MERGE_MUTATION = `mutation MergeOwnerPullRequest($id: ID!, $headOid: GitObjectID!) {
  mergePullRequest(input: {
    pullRequestId: $id,
    mergeMethod: SQUASH,
    expectedHeadOid: $headOid
  }) {
    pullRequest { merged }
  }
}`;

const defaultSleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function mergeCleanPullRequest({ github, core, pr, headOid }) {
  if (!headOid) {
    throw new Error(`Fresh head OID missing for PR #${pr.number}; refusing to merge`);
  }
  const result = await github.graphql(MERGE_MUTATION, {
    id: pr.node_id,
    headOid,
  });
  if (!result.mergePullRequest.pullRequest.merged) {
    throw new Error(`GitHub did not merge clean PR #${pr.number}`);
  }
  core.info(`Clean PR #${pr.number} squash-merged at expected head ${headOid}`);
  return "merged";
}

/**
 * Withdrawal is the safety direction, so it must be at least as robust as
 * arming. A transient GraphQL failure here would otherwise leave an armed
 * request live -- the job would go red, but the PR would still merge once
 * its checks passed. Bounded retries, same knobs as the arming path.
 */
async function withdrawArmedRequest({
  github,
  core,
  pr,
  reason,
  sleep,
  maxAttempts,
  retryDelayMs,
  initialState = null,
}) {
  let knownState = initialState;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const state = knownState || (await github.graphql(STATE_QUERY, { id: pr.node_id }));
      knownState = null;
      if (!state || !state.node) {
        throw new Error(`Fresh pull-request state unavailable for PR #${pr.number}`);
      }
      if (!state.node.autoMergeRequest) {
        core.info(`PR #${pr.number}: ${reason}; no armed request to withdraw.`);
        return "nothing-armed";
      }
      await github.graphql(DISABLE_MUTATION, { id: pr.node_id });
      core.warning(`PR #${pr.number}: auto-merge withdrawn -- ${reason}.`);
      return "withdrawn";
    } catch (error) {
      if (attempt === maxAttempts) throw error;
      core.warning(
        `PR #${pr.number}: withdrawal attempt ${attempt}/${maxAttempts} failed (${String(error)}); ` +
          `retrying in ${retryDelayMs}ms.`
      );
      await sleep(retryDelayMs);
    }
  }
  throw new Error(`Unable to withdraw auto-merge for PR #${pr.number}`);
}

function freshAdmissionBlock({
  state,
  trustedSender,
  repositoryOwner,
  repositoryNameWithOwner,
  expectedHeadOid,
}) {
  const node = state && state.node;
  if (!node) {
    return { code: "state-unavailable", reason: "fresh pull-request state unavailable" };
  }
  if (!node.labels || !Array.isArray(node.labels.nodes)) {
    return { code: "labels-unavailable", reason: "fresh pull-request labels unavailable" };
  }
  if (node.labels.pageInfo && node.labels.pageInfo.hasNextPage) {
    return { code: "labels-truncated", reason: "fresh pull-request labels exceed query bound" };
  }
  const labels = node.labels.nodes.map((label) => String(label && label.name).toLowerCase());
  if (labels.includes("no-automerge")) {
    return { code: "by-label", reason: "no-automerge label present" };
  }
  if (!trustedSender) {
    return {
      code: "untrusted-sender",
      reason: "event sent by someone other than the repository owner",
    };
  }
  if (node.isDraft !== false) {
    return { code: "draft", reason: "pull request is currently a draft" };
  }
  if (
    !node.author ||
    String(node.author.login).toLowerCase() !== String(repositoryOwner).toLowerCase()
  ) {
    return { code: "non-owner", reason: "pull request is not currently owner-authored" };
  }
  if (
    !node.headRepository ||
    !node.baseRepository ||
    node.headRepository.nameWithOwner !== repositoryNameWithOwner ||
    node.baseRepository.nameWithOwner !== repositoryNameWithOwner
  ) {
    return { code: "cross-repo", reason: "pull request is not currently same-repository" };
  }
  if (!node.headRefOid || node.headRefOid !== expectedHeadOid) {
    return { code: "stale-head", reason: "pull request head changed after this event" };
  }
  return null;
}

/**
 * Every pull_request event on an owner-authored same-repo PR reaches this
 * function. The event decides who triggered the run; the trusted base
 * controller queries GitHub for the current author, repositories, labels,
 * draft flag, merge state, and head OID before every attempt. Stale event
 * payload fields can therefore never arm or complete a merge.
 */
async function enableOrMergeOwnerPr({
  github,
  core,
  pr,
  trustedSender = true,
  repositoryOwner,
  repositoryNameWithOwner,
  sleep = defaultSleep,
  maxAttempts = 6,
  retryDelayMs = 5000,
}) {
  const retry = { sleep, maxAttempts, retryDelayMs };
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const state = await github.graphql(STATE_QUERY, { id: pr.node_id });
    const block = freshAdmissionBlock({
      state,
      trustedSender,
      repositoryOwner,
      repositoryNameWithOwner,
      expectedHeadOid: pr.head && pr.head.sha,
    });
    if (block) {
      // A delayed event for an older head must not mutate auto-merge state
      // that a newer event may already have established for the current head.
      // Current-state admission failures still withdraw below.
      if (block.code === "stale-head") {
        core.warning(`PR #${pr.number}: ${block.reason}; leaving current-head auto-merge state unchanged.`);
        return block.code;
      }
      const outcome = await withdrawArmedRequest({
        github,
        core,
        pr,
        reason: block.reason,
        initialState: state,
        ...retry,
      });
      return outcome === "withdrawn" ? `disabled-${block.code}` : block.code;
    }
    const existing = state.node.autoMergeRequest;
    if (existing) {
      if (existing.mergeMethod === "SQUASH") {
        core.info(`Auto-merge is already enabled for PR #${pr.number}`);
        return "already-enabled";
      }
      // This workflow promises squash merges. A request armed elsewhere with
      // MERGE or REBASE would otherwise ride through on our approval, so
      // replace it rather than trust it.
      await github.graphql(DISABLE_MUTATION, { id: pr.node_id });
      core.warning(`PR #${pr.number} had auto-merge armed with ${existing.mergeMethod}; replaced with SQUASH.`);
      // Re-query every admission field after changing state. A label or draft
      // transition during the mutation must be observed before re-arming.
      continue;
    }

    if (state.node.mergeStateStatus === "CLEAN") {
      return mergeCleanPullRequest({ github, core, pr, headOid: state.node.headRefOid });
    }

    try {
      await github.graphql(ENABLE_MUTATION, {
        id: pr.node_id,
        headOid: state.node.headRefOid,
      });
      core.info(`Auto-merge enabled for PR #${pr.number}`);
      return "enabled";
    } catch (error) {
      const message = String(error);
      if (/clean status/i.test(message)) {
        // The status and head may both have changed. Re-query them instead of
        // merging from the stale state that lost the race.
        if (attempt === maxAttempts) throw error;
        continue;
      }
      const transientMergeState = /unstable status/i.test(message);
      if (!transientMergeState || attempt === maxAttempts) {
        throw error;
      }
      core.warning(
        `GitHub has not stabilized PR #${pr.number} yet ` +
          `(attempt ${attempt}/${maxAttempts}); retrying in ${retryDelayMs}ms.`
      );
      await sleep(retryDelayMs);
    }
  }

  throw new Error(`Unable to enable or merge PR #${pr.number}`);
}

module.exports = { enableOrMergeOwnerPr, freshAdmissionBlock };
