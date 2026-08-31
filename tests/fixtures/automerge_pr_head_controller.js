"use strict";

// Fixture for the attack SH-2709 closes: a pull request that rewrites its own
// merge controller so it approves and merges itself whatever GitHub says about
// the PR state. It is what a PR head would contain if the workflow still loaded
// `.github/scripts/owner-automerge.js` from the PR checkout.
//
// It is a control as much as a fixture: the test runs it to prove the harness
// can detect a self-approving controller, then proves the workflow never loads
// this copy.

const MERGE_MUTATION = `mutation MergeOwnerPullRequest($id: ID!, $headOid: GitObjectID!) {
  mergePullRequest(input: {
    pullRequestId: $id,
    mergeMethod: SQUASH,
    expectedHeadOid: $headOid
  }) {
    pullRequest { merged }
  }
}`;

async function enableOrMergeOwnerPr({ github, core, pr }) {
  core.info("EVIL: merging PR #" + pr.number + " without consulting its state");
  const result = await github.graphql(MERGE_MUTATION, {
    id: pr.node_id,
    headOid: pr.head.sha,
  });
  if (!result.mergePullRequest.pullRequest.merged) {
    throw new Error("attack fixture merge was not reported as merged");
  }
  core.info("EVIL: merged PR #" + pr.number);
  return "merged";
}

module.exports = { enableOrMergeOwnerPr };
