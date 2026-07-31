"""Protect the runner policy for CrewScore CI.

The policy this file guards changed when the self-hosted DigitalOcean runner
was retired. It used to assert that routine validation ran on a persistent
self-hosted host *and* that only maintainer-owned pull requests were allowed
onto it -- the guard that keeps untrusted fork/bot code off a machine with
persistent state and credentials.

Every job now runs on ephemeral GitHub-hosted runners, which makes that
invariant vacuous: there is no persistent host to protect. So the tests below
enforce the stronger, simpler property instead -- *no* workflow may reintroduce
a self-hosted runner. If one is ever added back, the maintainer-only guard has
to come back with it, and this suite fails loudly rather than silently allowing
untrusted code onto a persistent machine.
"""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"


def _workflow(name: str) -> dict:
    return yaml.safe_load((WORKFLOW_DIR / name).read_text(encoding="utf-8"))


def _runs_on_values(workflow: dict) -> list:
    return [job.get("runs-on") for job in workflow.get("jobs", {}).values()]


def test_no_workflow_uses_a_self_hosted_runner():
    """The security invariant: nothing runs on a persistent host.

    A self-hosted runner keeps state and credentials between jobs, so running
    untrusted pull-request code on one is a compromise waiting to happen.
    Ephemeral hosted runners have no such exposure. Reintroducing a self-hosted
    runner means reintroducing a maintainer-only guard on every job that uses
    it -- fail here so that decision is deliberate.
    """
    offenders = []
    for path in sorted(WORKFLOW_DIR.glob("*.yml")):
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
        # Re-dump rather than scanning the raw file: comments explaining why
        # self-hosted runners were retired legitimately contain the phrase.
        # Dumping the parsed tree drops comments while still covering runner
        # labels hidden inside matrix strings, which a runs-on check misses.
        if "self-hosted" in yaml.safe_dump(parsed):
            offenders.append(path.name)
    assert offenders == [], f"self-hosted runner reintroduced in: {offenders}"


def test_routine_validation_runs_on_hosted_runners():
    for filename, job_names in {
        "pytest.yml": ("test", "browser"),
        "crewscore-selftest.yml": ("selftest",),
    }.items():
        jobs = _workflow(filename)["jobs"]
        for name in job_names:
            assert jobs[name]["runs-on"] == "ubuntu-latest", f"{filename}:{name}"


def test_validation_jobs_do_not_gate_on_pull_request_authorship():
    """Outside contributors get the same coverage as the maintainer.

    The authorship guards existed only to keep untrusted code off the
    self-hosted host. Retaining them on hosted runners would silently give fork
    PRs less validation than maintainer PRs, which is how a contributed
    regression reaches main unnoticed.
    """
    for filename, job_name in (
        ("pytest.yml", "test"),
        ("pytest.yml", "browser"),
        ("crewscore-selftest.yml", "selftest"),
    ):
        condition = _workflow(filename)["jobs"][job_name].get("if", "")
        assert "github.repository_owner" not in condition, f"{filename}:{job_name}"
        assert "head.repo.full_name" not in condition, f"{filename}:{job_name}"


def test_every_supported_python_version_is_validated():
    matrix = _workflow("pytest.yml")["jobs"]["test"]["strategy"]["matrix"]
    assert matrix["python-version"] == ["3.11", "3.12", "3.13"]


def test_consumer_example_uses_a_runner_available_in_a_new_repository():
    assert _workflow("example-ci.yml")["jobs"]["score"]["runs-on"] == "ubuntu-latest"


def test_selftest_only_runs_on_main_pushes_or_pull_requests():
    workflow = _workflow("crewscore-selftest.yml")
    assert workflow[True]["push"]["branches"] == ["main"]
    assert workflow[True]["pull_request"] is None


def test_release_verifies_on_all_three_platforms_and_publishes_ephemerally():
    """Windows and macOS verification is the point of the matrix.

    Those two exercise platform-specific behavior Linux cannot cover. Publishing
    and release-tag mutation stay on short-lived hosted workers with their
    dedicated trusted-publishing permissions.
    """
    release = _workflow("release.yml")["jobs"]
    verify = release["verify"]
    assert verify["runs-on"] == "${{ fromJSON(matrix.runner) }}"
    assert verify["strategy"]["matrix"]["include"] == [
        {"os": "Linux", "runner": '"ubuntu-latest"'},
        {"os": "Windows", "runner": '"windows-latest"'},
        {"os": "macOS", "runner": '"macos-latest"'},
    ]
    assert release["publish"]["runs-on"] == "ubuntu-latest"
    assert release["github-release"]["runs-on"] == "ubuntu-latest"
    assert release["floating-major-tag"]["runs-on"] == "ubuntu-latest"


def test_dependabot_security_changes_use_an_ephemeral_runner():
    """Dependency-update PRs run on GitHub-hosted infrastructure."""
    workflow = _workflow("dependabot-security-validation.yml")
    job = workflow["jobs"]["validate"]
    assert job["runs-on"] == "ubuntu-latest"
    assert "dependabot[bot]" in job["if"]
    assert "npm run test:web -- --workers=1" in str(job["steps"])
    assert any(step.get("uses") == "./" for step in job["steps"])
