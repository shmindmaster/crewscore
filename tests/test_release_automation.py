"""Agent-executable release and dist-pack generators stay honest."""

from __future__ import annotations

import json
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _workflow(name: str) -> dict:
    return yaml.safe_load(
        (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
    )


def test_owner_automerge_retries_transient_merge_state_and_fails_closed():
    workflow = (ROOT / ".github" / "workflows" / "auto-merge-owner-prs.yml").read_text(
        encoding="utf-8"
    )

    # A check_suite event has no pull_request payload and was therefore a dead trigger.
    assert "check_suite:" not in workflow
    assert "github.event.check_suite.head_sha" not in workflow

    result = subprocess.run(
        ["node", "--test", str(ROOT / ".github" / "scripts" / "owner-automerge.test.js")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_cut_release_dry_run_matches_package_version():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "cut_release.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    out = result.stdout
    assert "package_version=" in out
    assert "intended_tag=v" in out
    assert "changelog_section=ok" in out
    assert "dry_run=1" in out


def test_cut_release_script_does_not_claim_every_tag_push_starts_release():
    source = (ROOT / "scripts" / "cut_release.py").read_text(encoding="utf-8")
    assert "release_workflow=triggered_by_tag_push" not in source
    assert "next=confirm_release_workflow_started_for_{tag}" in source


def test_cut_release_dispatches_release_at_the_verified_exact_tag():
    """A GITHUB_TOKEN tag push cannot be the release-workflow handoff."""
    workflow = _workflow("cut-release-tag.yml")
    cut = workflow["jobs"]["cut"]
    handoff = workflow["jobs"]["handoff"]

    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] is False
    assert cut["permissions"] == {"contents": "write"}
    assert set(cut["outputs"]) == {"tag", "pushed"}

    assert handoff["needs"] == "cut"
    assert handoff["if"] == "needs.cut.outputs.pushed == 'true'"
    assert handoff["permissions"] == {"actions": "write", "contents": "read"}
    assert not any(
        str(step.get("uses", "")).startswith("actions/checkout@")
        for step in handoff["steps"]
    )

    script = handoff["steps"][0]["run"]
    assert '[[ ! "$TAG" =~ ^v[0-9]+\\.[0-9]+\\.[0-9]+$ ]]' in script
    assert 'git/ref/tags/${TAG}' in script
    assert 'TAG_OBJECT_TYPE" != "tag"' in script
    assert 'TARGET_TYPE" != "commit"' in script
    assert 'TARGET_SHA" != "$EXPECTED_SHA"' in script
    assert "gh workflow run release.yml" in script
    assert '--ref "$TAG"' in script
    assert "--raw-field dry-run=false" in script
    assert '--raw-field expected-sha="$EXPECTED_SHA"' in script


def test_release_dispatch_is_fail_safe_unless_ref_is_an_exact_release_tag():
    workflow = _workflow("release.yml")
    dispatch = workflow[True]["workflow_dispatch"]
    dry_run = dispatch["inputs"]["dry-run"]
    expected_sha = dispatch["inputs"]["expected-sha"]
    publish_condition = workflow["jobs"]["publish"]["if"]
    verify_steps = workflow["jobs"]["verify"]["steps"]

    assert dry_run == {
        "description": "Build and verify only; do not publish",
        "type": "boolean",
        "default": True,
    }
    assert expected_sha == {
        "description": "Required exact commit for a publishing dispatch",
        "type": "string",
        "required": False,
        "default": "",
    }
    assert "startsWith(github.ref, 'refs/tags/v')" in publish_condition
    assert "!inputs.dry-run" in publish_condition

    sha_guard = verify_steps[0]
    assert "!inputs.dry-run" in sha_guard["if"]
    assert sha_guard["env"]["EXPECTED_SHA"] == "${{ inputs.expected-sha }}"
    assert 'if [ -z "$EXPECTED_SHA" ]' in sha_guard["run"]
    assert 'GITHUB_SHA" != "$EXPECTED_SHA"' in sha_guard["run"]


def test_competitor_matrix_offline_writes_docs():
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_competitor_matrix.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    matrix = json.loads(
        (ROOT / "_production" / "competitors" / "agentlinter-matrix.json").read_text(
            encoding="utf-8"
        )
    )
    assert matrix["method"].startswith("public-docs")
    assert matrix["crewscore"]["live_adversarial"] is False
    assert matrix["crewscore"]["certification_claim"] is False
    md = (ROOT / "_production" / "competitors" / "agentlinter.md").read_text(encoding="utf-8")
    assert "CrewScore" in md and "AgentLinter" in md


def test_product_signals_offline_replaces_interview_pmf():
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "collect_product_signals.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(
        (ROOT / "_production" / "signals" / "latest.json").read_text(encoding="utf-8")
    )
    assert payload["automation_policy"]["pmf_interviews"] == "canceled"
    assert payload["package_version"]
    assert "interview" not in payload["method"].lower() or "replaces" in payload["method"]


def test_generate_dist_pack_writes_anti_promise_drafts(tmp_path: Path):
    out = tmp_path / "pack"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "generate_dist_pack.py"),
            "--output-dir",
            str(out),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert manifest["posts_automatically"] is False
    for filename in [
        "show-hn-title.txt",
        "show-hn-first-comment.md",
        "x-post.txt",
        "x-thread.md",
        "linkedin-post.md",
        "community-post.md",
        "answer-bank.md",
        "manifest.json",
        "checksums.txt",
    ]:
        assert (out / filename).is_file(), f"{filename} missing"
    for stale in ("0.6.2", "0.6.3", "0.6.8", "0.6.9"):
        assert stale not in result.stdout, f"script echoed stale release value {stale}"

    blob = (out / "show-hn-first-comment.md").read_text(encoding="utf-8").lower()
    normalized = re.sub(r"\s+", " ", blob)
    assert "red team" not in normalized
    assert "agent-guard" not in blob
    assert "prompt text is not uploaded" in normalized
    assert "anonymous allowlisted usage events may be sent unless you opt out" in normalized
    assert (out / "checksums.txt").is_file()

    # Deterministic checksum contract: manifest and generated artifacts are covered
    # (checksums.txt is excluded) and all digests are SHA-256 hex strings.
    checksums = (out / "checksums.txt").read_text(encoding="utf-8")
    rows = [line for line in checksums.splitlines() if line.strip()]
    assert rows
    expected_checksum_names = {
        "show-hn-title.txt",
        "show-hn-first-comment.md",
        "x-post.txt",
        "x-thread.md",
        "linkedin-post.md",
        "community-post.md",
        "answer-bank.md",
        "manifest.json",
    }
    parsed = {}
    for row in rows:
        assert "  " in row, f"invalid checksum row {row!r}"
        digest, name = row.split("  ", 1)
        assert re.fullmatch(r"[0-9a-f]{64}", digest), f"invalid checksum {row}"
        parsed[name] = digest
    assert set(parsed.keys()) == expected_checksum_names
    assert "checksums.txt" not in parsed
    for name, digest in parsed.items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
    assert manifest["checksum_excludes"] == ["checksums.txt"]


def test_generated_browser_engine_uses_repository_lf_endings() -> None:
    """Windows regeneration must not create a whole-file CRLF release diff."""
    engine = (ROOT / "score-engine.js").read_bytes()
    assert b"\r\n" not in engine


def test_generated_release_artifacts_force_lf_on_windows_checkout() -> None:
    """Git checkout must preserve the byte-pinned artifacts before tests run."""
    paths = ("score-engine.js", "docs/demo.svg")
    result = subprocess.run(
        ["git", "check-attr", "text", "eol", "--", *paths],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    attributes = {
        (path, attribute): value
        for path, attribute, value in (
            line.split(": ", 2) for line in result.stdout.splitlines()
        )
    }

    for path in paths:
        assert attributes[(path, "text")] == "set"
        assert attributes[(path, "eol")] == "lf"
        assert b"\r\n" not in (ROOT / path).read_bytes()
