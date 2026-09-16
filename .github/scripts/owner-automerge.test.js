"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { enableOrMergeOwnerPr } = require("./owner-automerge.js");

const pr = {
  number: 33,
  node_id: "PR_node",
  user: { login: "shmindmaster" },
  head: {
    sha: "faa4c2a71fc5378038a3760ff7d366fe551604c4",
    repo: { full_name: "shmindmaster/crewscore" },
  },
  base: { repo: { full_name: "shmindmaster/crewscore" } },
};
const freshHead = "faa4c2a71fc5378038a3760ff7d366fe551604c4";

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
  return {
    github,
    core,
    sleep,
    calls,
    sleeps,
    messages,
    repositoryOwner: "shmindmaster",
    repositoryNameWithOwner: "shmindmaster/crewscore",
  };
}

const state = (mergeStateStatus, autoMergeRequest = null, overrides = {}) => ({
  node: {
    mergeStateStatus,
    autoMergeRequest,
    headRefOid: freshHead,
    isDraft: false,
    author: { login: "shmindmaster" },
    headRepository: { nameWithOwner: "shmindmaster/crewscore" },
    baseRepository: { nameWithOwner: "shmindmaster/crewscore" },
    labels: { nodes: [], pageInfo: { hasNextPage: false } },
    ...overrides,
  },
});
test("retries UNSTABLE and enables auto-merge when checks are pending", async () => {
  const h = harness([
    state("UNSTABLE"),
    state("UNSTABLE"),
    new Error("Pull request is in unstable status"),
    state("BLOCKED"),
    state("BLOCKED"),
    { enablePullRequestAutoMerge: { clientMutationId: null } },
  ]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "enabled");
  assert.deepEqual(h.sleeps, [5000]);
});

test("an enable race reaching CLEAN refuses a direct merge", async () => {
  const h = harness([
    state("UNSTABLE"),
    state("UNSTABLE"),
    new Error("Pull request is in clean status"),
  ]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "clean-not-armed");
  assert.ok(!h.calls.some((call) => call.operation === "MergeOwnerPullRequest"));
});

test("an initially CLEAN pull request is never merged directly", async () => {
  const h = harness([state("CLEAN"), state("CLEAN")]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "clean-not-armed");
  assert.deepEqual(h.calls.map((call) => call.operation), [
    "OwnerAutoMergeState",
    "OwnerAutoMergeState",
  ]);
});

test("is idempotent when auto-merge is already enabled", async () => {
  const h = harness([state("BLOCKED", { enabledAt: "2026-07-31T00:00:00Z", mergeMethod: "SQUASH" })]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "already-enabled");
  assert.equal(h.calls.length, 1);
});

test("fails closed after bounded UNSTABLE retries", async () => {
  const responses = [];
  for (let attempt = 0; attempt < 6; attempt += 1) {
    responses.push(
      state("UNSTABLE"),
      state("UNSTABLE"),
      new Error("Pull request is in unstable status"),
    );
  }
  const h = harness(responses);
  await assert.rejects(enableOrMergeOwnerPr({ ...h, pr }), /unstable status/);
  assert.equal(h.calls.filter((call) => call.operation === "EnableOwnerAutoMerge").length, 6);
  assert.deepEqual(h.sleeps, [5000, 5000, 5000, 5000, 5000]);
});

test("propagates non-transient GraphQL failures", async () => {
  const h = harness([state("BLOCKED"), state("BLOCKED"), new Error("permission denied")]);
  await assert.rejects(enableOrMergeOwnerPr({ ...h, pr }), /permission denied/);
  assert.deepEqual(h.sleeps, []);
});

test("no-automerge withdraws an already-armed request instead of skipping", async () => {
  const h = harness([
    state(
      "BLOCKED",
      { enabledAt: "2026-07-31T00:00:00Z", mergeMethod: "SQUASH" },
      { labels: { nodes: [{ name: "no-automerge" }] } },
    ),
    { disablePullRequestAutoMerge: { clientMutationId: null } },
  ]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "disabled-by-label");
  assert.deepEqual(h.calls.map((call) => call.operation), [
    "OwnerAutoMergeState",
    "DisableOwnerAutoMerge",
  ]);
});

test("no-automerge with nothing armed neither enables nor merges, even when CLEAN", async () => {
  const h = harness([state("CLEAN", null, { labels: { nodes: [{ name: "no-automerge" }] } })]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "by-label");
  assert.equal(h.calls.length, 1);
});

test("a non-owner sender withdraws an armed request and never arms or merges", async () => {
  const h = harness([
    state("CLEAN", { enabledAt: "2026-07-31T00:00:00Z", mergeMethod: "SQUASH" }),
    { disablePullRequestAutoMerge: { clientMutationId: null } },
  ]);
  assert.equal(
    await enableOrMergeOwnerPr({ ...h, pr, trustedSender: false }),
    "disabled-untrusted-sender",
  );
  assert.deepEqual(h.calls.map((call) => call.operation), [
    "OwnerAutoMergeState",
    "DisableOwnerAutoMerge",
  ]);
  assert.ok(!h.calls.some((call) => /^(MergeOwnerPullRequest|EnableOwnerAutoMerge)$/.test(call.operation)));
});

test("a non-owner sender with nothing armed is a no-op, even when CLEAN", async () => {
  const h = harness([state("CLEAN")]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr, trustedSender: false }), "untrusted-sender");
  assert.equal(h.calls.length, 1);
});

test("withdrawal retries a transient failure instead of leaving the request armed", async () => {
  const h = harness([
    state(
      "BLOCKED",
      { enabledAt: "2026-07-31T00:00:00Z", mergeMethod: "SQUASH" },
      { labels: { nodes: [{ name: "no-automerge" }] } },
    ),
    new Error("Something went wrong while executing your query"),
    state(
      "BLOCKED",
      { enabledAt: "2026-07-31T00:00:00Z", mergeMethod: "SQUASH" },
      { labels: { nodes: [{ name: "no-automerge" }] } },
    ),
    { disablePullRequestAutoMerge: { clientMutationId: null } },
  ]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr, trustedSender: false }), "disabled-by-label");
  assert.deepEqual(h.sleeps, [5000]);
});

test("withdrawal fails loudly after bounded retries", async () => {
  const responses = [
    state(
      "BLOCKED",
      { enabledAt: "2026-07-31T00:00:00Z", mergeMethod: "SQUASH" },
      { labels: { nodes: [{ name: "no-automerge" }] } },
    ),
  ];
  for (let attempt = 0; attempt < 6; attempt += 1) responses.push(new Error("upstream unavailable"));
  const h = harness(responses);
  await assert.rejects(enableOrMergeOwnerPr({ ...h, pr, trustedSender: false }), /upstream unavailable/);
  assert.deepEqual(h.sleeps, [5000, 5000, 5000, 5000, 5000]);
});

test("replaces an existing non-squash auto-merge request with SQUASH", async () => {
  const h = harness([
    state("BLOCKED", { enabledAt: "2026-07-31T00:00:00Z", mergeMethod: "MERGE" }),
    { disablePullRequestAutoMerge: { clientMutationId: null } },
    state("BLOCKED"),
    state("BLOCKED"),
    { enablePullRequestAutoMerge: { clientMutationId: null } },
  ]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "enabled");
  assert.deepEqual(h.calls.map((call) => call.operation), [
    "OwnerAutoMergeState",
    "DisableOwnerAutoMerge",
    "OwnerAutoMergeState",
    "OwnerAutoMergeState",
    "EnableOwnerAutoMerge",
  ]);
  assert.ok(h.messages.some((message) => /replaced with SQUASH/.test(message)));
});

test("fresh draft state withdraws an armed request despite a ready event payload", async () => {
  const h = harness([
    state(
      "CLEAN",
      { enabledAt: "2026-07-31T00:00:00Z", mergeMethod: "SQUASH" },
      { isDraft: true },
    ),
    { disablePullRequestAutoMerge: { clientMutationId: null } },
  ]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "disabled-draft");
  assert.ok(!h.calls.some((call) => call.operation === "MergeOwnerPullRequest"));
});

test("a label added between admission reads blocks the clean path", async () => {
  const h = harness([
    state("CLEAN"),
    state("CLEAN", null, { labels: { nodes: [{ name: "no-automerge" }] } }),
  ]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "by-label");
  assert.deepEqual(h.calls.map((call) => call.operation), [
    "OwnerAutoMergeState",
    "OwnerAutoMergeState",
  ]);
});

test("a serialized stop event withdraws an in-flight event's armed request", async () => {
  const h = harness([
    // First event completes its already in-flight arming mutation.
    state("BLOCKED"),
    state("BLOCKED"),
    { enablePullRequestAutoMerge: { clientMutationId: null } },
    // cancel-in-progress: false lets the queued stop event run next. Its fresh
    // state observes both the label and the request that must be withdrawn.
    state(
      "BLOCKED",
      { enabledAt: "2026-09-16T00:00:00Z", mergeMethod: "SQUASH" },
      { labels: { nodes: [{ name: "no-automerge" }] } },
    ),
    { disablePullRequestAutoMerge: { clientMutationId: null } },
  ]);

  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "enabled");
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "disabled-by-label");
  assert.deepEqual(h.calls.map((call) => call.operation), [
    "OwnerAutoMergeState",
    "OwnerAutoMergeState",
    "EnableOwnerAutoMerge",
    "OwnerAutoMergeState",
    "DisableOwnerAutoMerge",
  ]);
});

test("a draft transition between admission reads prevents auto-merge arming", async () => {
  const h = harness([
    state("BLOCKED"),
    state("BLOCKED", null, { isDraft: true }),
  ]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "draft");
  assert.deepEqual(h.calls.map((call) => call.operation), [
    "OwnerAutoMergeState",
    "OwnerAutoMergeState",
  ]);
});

test("fresh owner state fails closed when the PR is no longer owner-authored", async () => {
  const h = harness([state("CLEAN", null, { author: { login: "someone-else" } })]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "non-owner");
  assert.ok(!h.calls.some((call) => /^(MergeOwnerPullRequest|EnableOwnerAutoMerge)$/.test(call.operation)));
});

test("missing trusted repository owner context fails closed", async () => {
  const h = harness([state("CLEAN")]);
  delete h.repositoryOwner;
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "non-owner");
  assert.ok(!h.calls.some((call) => /^(MergeOwnerPullRequest|EnableOwnerAutoMerge)$/.test(call.operation)));
});

test("a stale event head cannot arm or merge a newer pull-request head", async () => {
  const stalePr = { ...pr, head: { ...pr.head, sha: "1111111111111111111111111111111111111111" } };
  const h = harness([
    state("CLEAN", { enabledAt: "2026-07-31T00:00:00Z", mergeMethod: "SQUASH" }),
  ]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr: stalePr }), "stale-head");
  assert.deepEqual(h.calls.map((call) => call.operation), ["OwnerAutoMergeState"]);
});

test("enabling auto-merge is atomically bound to the fresh event head", async () => {
  const h = harness([
    state("BLOCKED"),
    state("BLOCKED"),
    { enablePullRequestAutoMerge: { clientMutationId: null } },
  ]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "enabled");
  assert.deepEqual(h.calls.at(-1), {
    operation: "EnableOwnerAutoMerge",
    variables: { id: pr.node_id, headOid: freshHead },
  });
});

test("a truncated fresh label set fails closed instead of missing the stop label", async () => {
  const h = harness([
    state("CLEAN", null, {
      labels: { nodes: [], pageInfo: { hasNextPage: true } },
    }),
  ]);
  assert.equal(await enableOrMergeOwnerPr({ ...h, pr }), "labels-truncated");
  assert.ok(!h.calls.some((call) => /^(MergeOwnerPullRequest|EnableOwnerAutoMerge)$/.test(call.operation)));
});
