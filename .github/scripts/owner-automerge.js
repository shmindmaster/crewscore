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

const defaultSleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

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

async function stopForAdmissionBlock({
  github,
  core,
  pr,
  state,
  trustedSender,
  repositoryOwner,
  repositoryNameWithOwner,
  retry,
}) {
  const block = freshAdmissionBlock({
    state,
    trustedSender,
    repositoryOwner,
    repositoryNameWithOwner,
    expectedHeadOid: pr.head && pr.head.sha,
  });
  if (!block) return null;

  // A delayed event for an older head must not mutate auto-merge state that a
  // newer event may already have established for the current head. Current-
  // state admission failures still withdraw below.
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

/**
 * Every pull_request event on an owner-authored same-repo PR reaches this
 * function. The event decides who triggered the run; the trusted base
 * controller queries GitHub for the current author, repositories, labels,
 * draft flag, merge state, and head OID at admission and again immediately
 * before every arm mutation. GitHub only offers an atomic precondition for the
 * head OID, not labels or draft state, so the second query narrows but cannot
 * eliminate the final API round-trip race. A subsequent label/draft event
 * withdraws an armed request. This controller never merges directly, because
 * an irreversible merge cannot be repaired after such a race.
 *
 * The historical function name remains for protected-base rollout
 * compatibility; despite that name, the current controller only reconciles
 * auto-merge state.
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
    const admissionOutcome = await stopForAdmissionBlock({
      github,
      core,
      pr,
      state,
      trustedSender,
      repositoryOwner,
      repositoryNameWithOwner,
      retry,
    });
    if (admissionOutcome) return admissionOutcome;
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

    // Re-query every mutable admission field immediately before an arm
    // mutation. expectedHeadOid gives the mutation an atomic head guard; no
    // equivalent GitHub precondition exists for labels or draft state.
    const mutationState = await github.graphql(STATE_QUERY, { id: pr.node_id });
    const preMutationOutcome = await stopForAdmissionBlock({
      github,
      core,
      pr,
      state: mutationState,
      trustedSender,
      repositoryOwner,
      repositoryNameWithOwner,
      retry,
    });
    if (preMutationOutcome) return preMutationOutcome;

    const currentExisting = mutationState.node.autoMergeRequest;
    if (currentExisting) {
      if (currentExisting.mergeMethod === "SQUASH") {
        core.info(`Auto-merge is already enabled for PR #${pr.number}`);
        return "already-enabled";
      }
      await github.graphql(DISABLE_MUTATION, { id: pr.node_id });
      core.warning(
        `PR #${pr.number} gained auto-merge with ${currentExisting.mergeMethod}; ` +
          "withdrew it before retrying SQUASH."
      );
      continue;
    }

    if (mutationState.node.mergeStateStatus === "CLEAN") {
      core.warning(
        `PR #${pr.number} is already clean; refusing an irreversible direct merge ` +
          "because labels and draft state cannot be atomically preconditioned."
      );
      return "clean-not-armed";
    }

    try {
      await github.graphql(ENABLE_MUTATION, {
        id: pr.node_id,
        headOid: mutationState.node.headRefOid,
      });
      core.info(`Auto-merge enabled for PR #${pr.number}`);
      return "enabled";
    } catch (error) {
      const message = String(error);
      if (/clean status/i.test(message)) {
        core.warning(
          `PR #${pr.number} became clean before auto-merge could be armed; ` +
            "refusing an irreversible direct merge."
        );
        return "clean-not-armed";
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
