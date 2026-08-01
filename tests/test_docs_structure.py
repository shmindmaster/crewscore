"""Active documentation set stays complete, linked, and drift-checked."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from crewscore import __version__
from crewscore.scoring import RULESET_ID

ROOT = Path(__file__).resolve().parents[1]

# Canonical active docs (stubs for old names are listed separately).
CANONICAL_DOCS = (
    "architecture.md",
    "scoring-and-controls.md",
    "validation.md",
    "validation-corpus.md",
    "cli.md",
    "github-action.md",
    "development.md",
    "policies.md",
    "next-steps-eval.md",
    "roadmap.md",
    "automation.md",
)

# Old paths kept as redirects so external links do not 404 in-repo.
REDIRECT_DOCS = (
    "scoring.md",
    "scoring-governance.md",
    "ci.md",
)


def test_canonical_and_redirect_docs_exist():
    for name in CANONICAL_DOCS + REDIRECT_DOCS:
        path = ROOT / "docs" / name
        assert path.is_file(), f"missing docs/{name}"
        assert path.stat().st_size > 40, f"docs/{name} looks empty"


def test_redirect_docs_point_at_canonical_pages():
    scoring = (ROOT / "docs" / "scoring.md").read_text(encoding="utf-8")
    assert "scoring-and-controls.md" in scoring
    gov = (ROOT / "docs" / "scoring-governance.md").read_text(encoding="utf-8")
    assert "scoring-and-controls.md" in gov
    ci = (ROOT / "docs" / "ci.md").read_text(encoding="utf-8")
    assert "github-action.md" in ci


def test_readme_docs_table_links_canonical_pages():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for path in (
        "docs/scoring-and-controls.md",
        "docs/github-action.md",
        "docs/development.md",
        "docs/architecture.md",
        "docs/validation.md",
        "docs/cli.md",
    ):
        assert path in readme, f"README missing link to {path}"


def test_cli_help_lists_primary_and_secondary_commands():
    from click.testing import CliRunner

    from crewscore.cli import main

    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    for cmd in (
        "test",
        "scan",
        "fix",
        "rules",
        "baseline",
        "init",
        "export-eval",
        "assess-vendor",
    ):
        assert cmd in result.output, f"CLI help missing {cmd}"


def test_action_yml_name_and_key_inputs_match_github_action_doc():
    action = yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))
    doc = (ROOT / "docs" / "github-action.md").read_text(encoding="utf-8")
    assert action["name"] == "CrewScore"
    for key in (
        "prompt-file",
        "scan-path",
        "required-controls",
        "baseline",
        "fail-on-regression",
        "sarif",
        "max-smells",
    ):
        assert key in action["inputs"], key
        assert f"`{key}`" in doc or key in doc, f"github-action.md missing {key}"


def test_package_version_and_ruleset_appear_in_validation_docs():
    """Avoid silent version/ruleset drift in methodology pages."""
    validation = (ROOT / "docs" / "validation.md").read_text(encoding="utf-8")
    corpus = (ROOT / "docs" / "validation-corpus.md").read_text(encoding="utf-8")
    assert RULESET_ID in validation or RULESET_ID in corpus
    assert __version__ in validation
    assert __version__ in corpus
    assert re.search(r"crewscore-hygiene@\d+\.\d+\.\d+", validation + corpus)


def test_scoring_and_controls_states_formula_and_control_count():
    text = (ROOT / "docs" / "scoring-and-controls.md").read_text(encoding="utf-8")
    assert "23" in text
    assert "dimension_score" in text or "controls_covered" in text
    assert "evidence-backed" in text
    assert "Scoring governance" in text
