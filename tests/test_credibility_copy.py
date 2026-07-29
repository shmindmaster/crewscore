"""Public copy must preserve CrewScore's written-control evidence boundary."""

from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def test_comparison_describes_written_controls_not_production_harm():
    text = (REPO / "docs" / "comparison.md").read_text(encoding="utf-8").lower()
    assert "will this agent hurt someone in production" not in text
    assert "which published written controls does this system prompt not state" in text
    assert "not a prediction of runtime behavior" in text


def test_live_eval_guide_uses_selected_controls_not_an_arbitrary_score_gate():
    text = (REPO / "docs" / "next-steps-eval.md").read_text(encoding="utf-8").lower()
    assert "--threshold 50" not in text
    assert "--require human_gate.approval_required,safe_stop.stop_condition" in text
    assert "after selecting the written controls your product needs" in text


def test_public_ci_examples_use_explicit_controls_not_an_arbitrary_score_gate():
    paths = (
        REPO / ".github" / "workflows" / "example-ci.yml",
        REPO / "docs" / "ci.md",
        REPO / "docs" / "cli.md",
        REPO / "assets" / "site.js",
        REPO / "crewscore" / "export_eval.py",
    )
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
    assert "--threshold 50" not in text
    assert 'threshold: "50"' not in text
    assert "required-controls" in text


def test_validation_documentation_is_honest_about_the_optional_corpus_cache():
    text = " ".join(
        (REPO / "docs" / "validation.md").read_text(encoding="utf-8").lower().split()
    )
    assert "when the pinned corpus cache is materialized" in text
    assert "routine ci does not download or redistribute the source prompts" in text


def test_readme_scopes_the_14_of_100_median_to_production_prompts():
    text = (REPO / "README.md").read_text(encoding="utf-8").lower()
    assert "83 production prompts" in text
    assert "among the production subset, median coverage was 14" in text
    assert "the median states 14 of 100" not in text


def test_live_eval_scoring_charter_link_targets_the_current_document():
    text = (REPO / "docs" / "next-steps-eval.md").read_text(encoding="utf-8")
    assert "[Scoring charter](scoring.md#charter)" in text


def test_vendor_cli_uses_self_attestation_language_not_a_credibility_verdict():
    text = (REPO / "crewscore" / "vendor_scorecard.py").read_text(encoding="utf-8").lower()
    assert "production credibility" not in text
    assert "production-proven" not in text
    assert "self-attested" in text
    assert "not an independent audit" in text
