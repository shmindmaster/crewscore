"use strict";

const STATE_QUERY = `query OwnerAutoMergeState($id: ID!) {
  node(id: $id) {
    ... on PullRequest {
      autoMergeRequest { enabledAt }
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

const MERGE_MUTATION = `mutation MergeOwnerPullRequest($id: ID!, $headOid: GitObjectID!) {
  mergePullRequest(input: {
    pullRequestId: $id,
    mergeMethod: SQUASH,
    expectedHeadOid: $headOid
  }) {
    pullRequest { merged }
  }
}`;

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

async function enableOrMergeOwnerPr({
  github,
  core,
  pr,
  sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)),
  maxAttempts = 6,
  retryDelayMs = 5000,
}) {
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const state = await github.graphql(STATE_QUERY, { id: pr.node_id });
    if (state.node.autoMergeRequest) {
      core.info(`Auto-merge is already enabled for PR #${pr.number}`);
      return "already-enabled";
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
