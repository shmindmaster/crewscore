"""Supply-chain and decision-provenance guards for CrewScore's own CI.

Three invariants, each one careless edit away from being lost silently:

1. Third-party GitHub Actions are pinned to immutable commit SHAs. A mutable
   tag (`@v7`, `@main`) can be repointed by whoever controls that repository,
   and the jobs holding write permissions or an OIDC identity token are exactly
   the ones worth attacking.
2. Each pin carries its version in an adjacent comment. A bare SHA is
   unreviewable and un-updatable; `# vX.Y.Z` is what lets a human (and
   Dependabot) see and bump what the SHA actually is.
3. The workflow that decides whether a pull request auto-merges must not take
   its decision code from that pull request. Loading
   `.github/scripts/owner-automerge.js` from the PR head made the PR the judge
   of itself. It now comes from a checkout of the protected base revision.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
HARNESS = FIXTURE_DIR / "automerge_controller_harness.js"
PR_HEAD_CONTROLLER = FIXTURE_DIR / "automerge_pr_head_controller.js"

AUTOMERGE_WORKFLOW = "auto-merge-owner-prs.yml"
CONTROLLER_REL = ".github/scripts/owner-automerge.js"
BASE_CHECKOUT_PATH = ".github-base"

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_COMMENT_RE = re.compile(r"#\s*(?:v\d|release/v\d)", re.IGNORECASE)
CONTROLLER_LITERAL_RE = re.compile(r"""["']([^"']*owner-automerge\.js)["']""")

NODE = shutil.which("node")


def _workflow_paths() -> list[Path]:
    return sorted(WORKFLOW_DIR.glob("*.yml"))


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _is_third_party(uses: str) -> bool:
    if not uses or uses.startswith(("./", "../", "docker://")):
        return False
    return "/" in uses.split("@", 1)[0]


def _split_ref(uses: str) -> tuple[str, str]:
    action, _, ref = uses.partition("@")
    return action, ref


def _effective_permissions(workflow: dict, job: dict) -> dict:
    """Top-level permissions, overridden per job, as the runner resolves them."""
    permissions: dict = {}
    for level in (workflow.get("permissions"), job.get("permissions")):
        if isinstance(level, dict):
            permissions.update(level)
        elif level == "write-all":
            return {"*": "write"}
    return permissions


def _is_privileged(permissions: dict) -> bool:
    return any(value == "write" for value in permissions.values())


def _job_uses(job: dict) -> list[str]:
    return [step.get("uses") for step in job.get("steps", []) or []]


def _controller_step(workflow: dict):
    """The github-script step that decides whether the PR auto-merges."""
    for job in workflow.get("jobs", {}).values():
        for step in job.get("steps", []) or []:
            if str(step.get("uses", "")).startswith("actions/github-script@"):
                return job, step
    return None, None


def _pinned_uses_lines(path: Path):
    """Every live `uses:` of a third-party action, with its raw line."""
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        match = re.match(r"^(?:\s*-\s+)?uses:\s*(\S+)\s*(.*)$", line)
        if not match:
            continue
        uses, trailing = match.group(1), match.group(2)
        if not _is_third_party(uses):
            continue
        yield number, uses, trailing


def test_privileged_jobs_pin_every_third_party_action_to_a_commit_sha():
    """The SH-2709 headline: write/OIDC jobs never run a movable reference.

    `actions/checkout@v7` is a pointer someone else controls. In a job holding
    `contents: write` or an OIDC token, moving that pointer is remote code
    execution with our release credentials attached.
    """
    offenders = []
    for path in _workflow_paths():
        workflow = _load(path)
        for job_name, job in (workflow.get("jobs") or {}).items():
            permissions = _effective_permissions(workflow, job)
            if not _is_privileged(permissions):
                continue
            for uses in _job_uses(job):
                if not _is_third_party(uses):
                    continue
                action, ref = _split_ref(uses)
                if not FULL_SHA_RE.match(ref):
                    offenders.append(f"{path.name}:{job_name}:{action}@{ref}")
    assert offenders == [], f"mutable action refs in privileged jobs: {offenders}"


def test_no_mutable_third_party_action_ref_anywhere():
    """Unprivileged jobs too: pinning is cheap, triage is expensive.

    A read-only job still runs the action's code with a `GITHUB_TOKEN` in the
    environment, so an unpinned step anywhere is a step nobody reviewed.
    """
    offenders = []
    for path in _workflow_paths():
        workflow = _load(path)
        for job_name, job in (workflow.get("jobs") or {}).items():
            for uses in _job_uses(job):
                if not _is_third_party(uses):
                    continue
                action, ref = _split_ref(uses)
                if not FULL_SHA_RE.match(ref):
                    offenders.append(f"{path.name}:{job_name}:{action}@{ref}")
    assert offenders == [], f"mutable action refs: {offenders}"


def test_every_pinned_action_records_its_version_in_an_adjacent_comment():
    """A bare 40-char SHA tells a reviewer nothing and blocks Dependabot.

    The comment is the reviewable half of the pin: it is what a human reads in
    a diff, and what Dependabot matches on when it proposes the next SHA bump.
    """
    offenders = []
    for path in _workflow_paths():
        for number, uses, trailing in _pinned_uses_lines(path):
            _, ref = _split_ref(uses)
            if not FULL_SHA_RE.match(ref):
                continue
            if not VERSION_COMMENT_RE.search(trailing):
                offenders.append(f"{path.name}:{number}:{uses}")
    assert offenders == [], f"pins without a version comment: {offenders}"


def test_each_action_resolves_to_one_sha_across_all_workflows():
    """Two SHAs for one action is drift, and half of it is stale.

    Dependabot bumps every occurrence in one PR, so divergent pins mean someone
    hand-edited a workflow and left an older (unpatched) copy behind.
    """
    resolved: dict[str, set[str]] = {}
    for path in _workflow_paths():
        workflow = _load(path)
        for job in (workflow.get("jobs") or {}).values():
            for uses in _job_uses(job):
                if not _is_third_party(uses):
                    continue
                action, ref = _split_ref(uses)
                resolved.setdefault(action, set()).add(ref)
    divergent = {
        action: sorted(refs) for action, refs in resolved.items() if len(refs) > 1
    }
    assert divergent == {}, f"actions pinned to more than one SHA: {divergent}"


def test_automerge_controller_is_loaded_from_the_base_revision():
    """The confused-deputy fix: the PR must not supply its own judge.

    Requiring the controller out of `GITHUB_WORKSPACE` resolves inside the PR
    checkout, so a PR could ship a controller that approves anything. Every
    reference to the controller in this workflow has to come from the
    base-revision checkout instead.
    """
    workflow = _load(WORKFLOW_DIR / AUTOMERGE_WORKFLOW)
    _, step = _controller_step(workflow)
    assert step is not None, "no github-script step left in the auto-merge workflow"

    script = step.get("with", {}).get("script", "")
    paths = CONTROLLER_LITERAL_RE.findall(script)
    assert paths, "the workflow no longer loads the auto-merge controller"

    offenders = [p for p in paths if not p.startswith(BASE_CHECKOUT_PATH + "/")]
    assert offenders == [], (
        "controller loaded from a path the pull request controls: "
        f"{offenders}. The decision code must come from {BASE_CHECKOUT_PATH}/."
    )
    assert f"{BASE_CHECKOUT_PATH}/{CONTROLLER_REL}" in paths


def test_automerge_base_checkout_is_pinned_immutable_and_credential_free():
    """The base checkout is the whole mitigation; check its properties."""
    workflow = _load(WORKFLOW_DIR / AUTOMERGE_WORKFLOW)
    checkouts = [
        step
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if str(step.get("uses", "")).startswith("actions/checkout@")
    ]
    base = [step for step in checkouts if step.get("with", {}).get("ref")]
    assert len(base) == 1, "expected exactly one checkout pinned to a ref"

    step = base[0]
    _, ref = _split_ref(step["uses"])
    assert FULL_SHA_RE.match(ref), f"base checkout is not pinned to a SHA: {ref}"
    assert step["with"]["ref"] == "${{ github.event.pull_request.base.sha }}"
    assert step["with"]["path"] == BASE_CHECKOUT_PATH
    assert step["with"]["persist-credentials"] is False


def test_automerge_keeps_its_existing_mitigations():
    """Hardening must not trade away the guardrails that were already there."""
    workflow = _load(WORKFLOW_DIR / AUTOMERGE_WORKFLOW)
    job = workflow["jobs"]["enable-automerge"]
    condition = job["if"]

    permissions = _effective_permissions(workflow, job)
    assert permissions.get("contents") == "write"
    assert permissions.get("pull-requests") == "write"
    # Least privilege: no scope beyond the two this job needs, and no OIDC.
    assert set(permissions) == {"contents", "pull-requests"}
    assert "id-token" not in permissions

    assert "github.repository_owner" in condition
    assert "head.repo.full_name" in condition
    assert "no-automerge" in condition

    controller = (ROOT / CONTROLLER_REL).read_text(encoding="utf-8")
    assert "expectedHeadOid" in controller
    assert "pr.head.sha" in controller
    assert "mergeMethod: SQUASH" in controller


@pytest.mark.skipif(
    NODE is None, reason="node is required to execute the JS merge controller"
)
def test_a_pull_request_cannot_approve_itself_by_editing_the_controller(tmp_path):
    """Fixture attack: a PR rewrites the controller, and is ignored.

    Two checkouts are built the way the workflow builds them - a base tree
    holding the reviewed controller, and a PR tree holding one that merges
    unconditionally. Both are driven through the same harness against a fake
    GitHub that reports the PR as blocked. The base copy must refuse; the PR
    copy must be shown to merge, which proves the harness can actually detect
    the attack rather than passing by accident.
    """
    base_root = tmp_path / "base"
    pr_root = tmp_path / "pr"
    for root in (base_root, pr_root):
        (root / ".github" / "scripts").mkdir(parents=True)
    shutil.copyfile(ROOT / CONTROLLER_REL, base_root / CONTROLLER_REL)
    shutil.copyfile(PR_HEAD_CONTROLLER, pr_root / CONTROLLER_REL)

    base_run = _run_harness(base_root)
    assert base_run["controllerPath"] == str(base_root / CONTROLLER_REL)
    assert base_run["outcome"].startswith("refused"), base_run
    assert "OwnerAutoMergeState" in base_run["calls"][0], base_run
    assert not any("MergeOwnerPullRequest" in call for call in base_run["calls"]), (
        "the reviewed controller merged a pull request GitHub reports as blocked"
    )

    attack_run = _run_harness(pr_root)
    assert attack_run["outcome"] == "merged", (
        "the attack fixture no longer merges anything, so this test proves nothing"
    )

    # The workflow's constant is what selects between the two trees above.
    paths = CONTROLLER_LITERAL_RE.findall(
        _controller_step(_load(WORKFLOW_DIR / AUTOMERGE_WORKFLOW))[1]["with"]["script"]
    )
    assert [p for p in paths if p.endswith(CONTROLLER_REL)], paths
    assert all(p.startswith(BASE_CHECKOUT_PATH + "/") for p in paths), paths


def _run_harness(checkout_root: Path) -> dict:
    completed = subprocess.run(
        [NODE, str(HARNESS), str(checkout_root)],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    lines = [line for line in completed.stdout.splitlines() if line.startswith("{")]
    assert lines, f"harness produced no JSON on {checkout_root}: {completed.stdout}"
    return json.loads(lines[-1])
