"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { enableOrMergeOwnerPr } = require("./owner-automerge.js");

const pr = {
  number: 33,
  node_id: "PR_node",
  head: { sha: "faa4c2a71fc5378038a3760ff7d366fe551604c4" },
};

function harness(responses) {
  const calls = [];
  const sleeps = [];
  const messages = [];
  const github = {
    graphql: async (document, variables) => {
      const operation = document.match(/(?:query|mutation) (\w+)/)[1];
      calls.push({ operation, variables });
      const response = responses.shift();
      if (response instanceof Error) throw response;
      return response;
    },
  };
  const core = {
    info: (message) => messages.push(message),
    warning: (message) => messages.push(message),
  };
  const sleep = async (milliseconds) => sleeps.push(milliseconds);
  return { github, core, sleep, calls, sleeps, messages };
}

const state = (mergeStateStatus, autoMergeRequest = null) => ({
  node: { mergeStateStatus, autoMergeRequest },
});
const merged = { mergePullRequest: { pullRequest: { merged: true } } };

test("retries UNSTABLE and enables auto-merge when checks are pending", async () => {
  const h = harness([
    state("UNSTABLE"),
    new Error("Pull request is in unstable status"),
    state("BLOCKED"),
    { enablePullRequestAutoMerge: { clientMutationId: null } },
  ]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "enabled");
  assert.deepEqual(h.sleeps, [5000]);
});

test("merges with the exact head when an enable race reaches CLEAN", async () => {
  const h = harness([
    state("UNSTABLE"),
    new Error("Pull request is in clean status"),
    merged,
  ]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "merged");
  assert.deepEqual(h.calls.at(-1), {
    operation: "MergeOwnerPullRequest",
    variables: { id: pr.node_id, headOid: pr.head.sha },
  });
});

test("merges an initially CLEAN pull request", async () => {
  const h = harness([state("CLEAN"), merged]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "merged");
  assert.deepEqual(h.calls.map((call) => call.operation), [
    "OwnerAutoMergeState",
    "MergeOwnerPullRequest",
  ]);
});

test("is idempotent when auto-merge is already enabled", async () => {
  const h = harness([state("BLOCKED", { enabledAt: "2026-07-31T00:00:00Z" })]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "already-enabled");
  assert.equal(h.calls.length, 1);
});

test("fails closed after bounded UNSTABLE retries", async () => {
  const responses = [];
  for (let attempt = 0; attempt < 6; attempt += 1) {
    responses.push(state("UNSTABLE"), new Error("Pull request is in unstable status"));
  }
  const h = harness(responses);
  await assert.rejects(enableOrMergeOwnerPr({ ...h, pr }), /unstable status/);
  assert.equal(h.calls.filter((call) => call.operation === "EnableOwnerAutoMerge").length, 6);
  assert.deepEqual(h.sleeps, [5000, 5000, 5000, 5000, 5000]);
});

test("propagates non-transient GraphQL failures", async () => {
  const h = harness([state("BLOCKED"), new Error("permission denied")]);
  await assert.rejects(enableOrMergeOwnerPr({ ...h, pr }), /permission denied/);
  assert.deepEqual(h.sleeps, []);
});
