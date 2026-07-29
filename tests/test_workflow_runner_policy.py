"""Protect the DigitalOcean runner policy for routine CrewScore validation."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ["self-hosted", "Linux", "X64", "sh-runner", "docker"]


def _workflow(name: str) -> dict:
    return yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"))


def test_routine_validation_uses_the_digitalocean_runner_with_exact_labels():
    workflows = {
        "pytest.yml": ("test", "browser"),
        "crewscore-selftest.yml": ("selftest",),
        "example-ci.yml": ("score",),
    }
    for filename, job_names in workflows.items():
        jobs = _workflow(filename)["jobs"]
        for name in job_names:
            assert jobs[name]["runs-on"] == RUNNER, f"{filename}:{name}"


def test_persistent_runner_jobs_refuse_fork_originated_pull_request_code():
    for filename, job_name in (("pytest.yml", "test"), ("pytest.yml", "browser"), ("crewscore-selftest.yml", "selftest")):
        condition = _workflow(filename)["jobs"][job_name].get("if", "")
        assert "github.event_name != 'pull_request'" in condition, f"{filename}:{job_name}"
        assert "head.repo.full_name == github.repository" in condition, f"{filename}:{job_name}"


def test_selftest_only_runs_on_main_pushes_or_pull_requests():
    workflow = _workflow("crewscore-selftest.yml")
    assert workflow[True]["push"]["branches"] == ["main"]
    assert workflow[True]["pull_request"] is None


def test_release_publishing_stays_isolated_from_routine_runner_compute():
    """Trusted release/PyPI jobs remain on GitHub-hosted ephemeral workers.

    They run only from tags/manual dispatch and hold OIDC release permissions;
    this is a deliberate exception, not a routine validation-minute sink.
    """
    release = _workflow("release.yml")["jobs"]
    assert release["verify"]["runs-on"] == "${{ matrix.os }}"
    assert release["publish"]["runs-on"] == "ubuntu-latest"
