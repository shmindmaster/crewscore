"use strict";

const STATE_QUERY = `query OwnerAutoMergeState($id: ID!) {
  node(id: $id) {
    ... on PullRequest {
      autoMergeRequest { enabledAt mergeMethod }
      mergeStateStatus
    }
  }
}`;

const ENABLE_MUTATION = `mutation EnableOwnerAutoMerge($id: ID!) {
  enablePullRequestAutoMerge(input: {
    pullRequestId: $id,
    mergeMethod: SQUASH
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

async function mergeCleanPullRequest({ github, core, pr }) {
  const result = await github.graphql(MERGE_MUTATION, {
    id: pr.node_id,
    headOid: pr.head.sha,
  });
  if (!result.mergePullRequest.pullRequest.merged) {
    throw new Error(`GitHub did not merge clean PR #${pr.number}`);
  }
  core.info(`Clean PR #${pr.number} squash-merged at expected head ${pr.head.sha}`);
  return "merged";
}

/**
 * Withdrawal is the safety direction, so it must be at least as robust as
 * arming. A transient GraphQL failure here would otherwise leave an armed
 * request live -- the job would go red, but the PR would still merge once
 * its checks passed. Bounded retries, same knobs as the arming path.
 */
async function withdrawArmedRequest({ github, core, pr, reason, sleep, maxAttempts, retryDelayMs }) {
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const state = await github.graphql(STATE_QUERY, { id: pr.node_id });
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

/**
 * Every pull_request event on an owner-authored same-repo PR reaches this
 * function. Only an event *sent by the owner* on a PR *without* the
 * `no-automerge` label may arm or complete a merge. Every other event --
 * a collaborator pushing to the owner's branch, anyone applying the stop
 * label -- may only withdraw. Filtering those events out at the workflow
 * level was the earlier design, and it left armed requests live precisely
 * when they most needed revoking.
 */
async function enableOrMergeOwnerPr({
  github,
  core,
  pr,
  optOut = false,
  trustedSender = true,
  sleep = defaultSleep,
  maxAttempts = 6,
  retryDelayMs = 5000,
}) {
  const retry = { sleep, maxAttempts, retryDelayMs };
  if (optOut) {
    const outcome = await withdrawArmedRequest({ github, core, pr, reason: "no-automerge label present", ...retry });
    return outcome === "withdrawn" ? "disabled-by-label" : "opted-out";
  }
  if (!trustedSender) {
    const outcome = await withdrawArmedRequest({
      github,
      core,
      pr,
      reason: "event sent by someone other than the repository owner",
      ...retry,
    });
    return outcome === "withdrawn" ? "disabled-untrusted-sender" : "untrusted-sender";
  }

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const state = await github.graphql(STATE_QUERY, { id: pr.node_id });
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
    }

    if (state.node.mergeStateStatus === "CLEAN") {
      return mergeCleanPullRequest({ github, core, pr });
    }

    try {
      await github.graphql(ENABLE_MUTATION, { id: pr.node_id });
      core.info(`Auto-merge enabled for PR #${pr.number}`);
      return "enabled";
    } catch (error) {
      const message = String(error);
      if (/clean status/i.test(message)) {
        return mergeCleanPullRequest({ github, core, pr });
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

module.exports = { enableOrMergeOwnerPr };
