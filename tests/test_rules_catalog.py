"""Transparency: open rules catalog is complete and non-black-box."""

import json
from pathlib import Path

from click.testing import CliRunner

from crewscore.cli import main
from crewscore.rules_catalog import (
    DIMENSION_PROVENANCE,
    PROVENANCE_GRADES,
    SCORING_METHOD,
    catalog_payload,
    demo_formula,
    list_rules,
    scoring_transparency_block,
)
from crewscore.scorers.structural_analysis import SCORER_MAP
from crewscore.scoring import DIMENSION_KEYS, RULESET_ID


def test_every_dimension_declares_its_provenance():
    """No dimension gets to stay silent about where its rules came from."""
    assert set(DIMENSION_PROVENANCE) == set(DIMENSION_KEYS)
    for key, entry in DIMENSION_PROVENANCE.items():
        assert entry["grade"] in PROVENANCE_GRADES, key
        assert entry["rationale"].strip(), key


def test_evidence_backed_claims_carry_citations():
    """Claiming external evidence requires naming it."""
    for key, entry in DIMENSION_PROVENANCE.items():
        if entry["grade"] == "evidence-backed":
            assert entry["citations"], f"{key} claims evidence with no citation"


def test_weakest_dimension_is_labelled_honestly():
    """Compliance is keyword presence; the catalog must not imply otherwise."""
    assert DIMENSION_PROVENANCE["compliance"]["grade"] == "author-intuition"


def test_rules_and_payload_expose_provenance():
    for rule in list_rules():
        assert rule["provenance"] in PROVENANCE_GRADES
    payload = catalog_payload()
    assert payload["provenance_grades"] == PROVENANCE_GRADES
    for dim in payload["dimensions"]:
        assert dim["grade"] in PROVENANCE_GRADES


def test_console_strings_survive_legacy_windows_encoding():
    """Regression: U+2192 in the formula crashed `crewscore rules` on cp1252.

    Windows redirects stdout through the ANSI code page, so any character
    outside cp1252 in a printed string takes the command down.
    """
    printed = [
        SCORING_METHOD["dimension_score_formula"],
        SCORING_METHOD["overall_score_formula"],
        *SCORING_METHOD["what_this_is_not"],
        *PROVENANCE_GRADES.values(),
        *(e["rationale"] for e in DIMENSION_PROVENANCE.values()),
        *(c for e in DIMENSION_PROVENANCE.values() for c in e["citations"]),
    ]
    for text in printed:
        text.encode("cp1252")  # raises UnicodeEncodeError on regression


def test_every_scorer_pattern_is_in_open_catalog():
    rules = list_rules()
    ids = {r["rule_id"] for r in rules}
    expected = {rid for patterns in SCORER_MAP.values() for rid, _ in patterns}
    assert ids == expected
    assert len(rules) >= 20


def test_catalog_has_formula_and_source():
    payload = catalog_payload()
    assert payload["ruleset"] == RULESET_ID
    assert payload["method"]["llm_calls"] is False
    assert "matches" in payload["method"]["dimension_score_formula"]
    assert "structural_analysis.py" in payload["method"]["source_of_truth"]
    assert payload["rule_count"] == len(list_rules())


def test_demo_formula_matches_documented_math():
    assert demo_formula(0, 8) == 0
    assert demo_formula(1, 8) == min(100, round(15 + 85 * (1 / 8)))
    assert demo_formula(8, 8) == 100


def test_cli_rules_human_lists_rule_ids():
    runner = CliRunner()
    result = runner.invoke(main, ["rules"])
    assert result.exit_code == 0, result.output
    assert RULESET_ID in result.output
    assert "injection.01" in result.output
    assert "deterministic" in result.output.lower() or "regex" in result.output.lower()
    assert "not" in result.output.lower()  # anti-promise


def test_cli_rules_json_is_complete():
    runner = CliRunner()
    result = runner.invoke(main, ["rules", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ruleset"] == RULESET_ID
    assert payload["rule_count"] == len(payload["rules"])
    assert all("pattern" in r and "rule_id" in r for r in payload["rules"])
    assert payload["method"]["api_key_required"] is False


def test_cli_rules_filter_dimension():
    runner = CliRunner()
    result = runner.invoke(main, ["rules", "--json", "--dimension", "cost"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["rule_count"] > 0
    assert all(r["dimension"] == "cost" for r in payload["rules"])


def test_test_json_always_includes_findings_and_transparency():
    """JSON is never a black box — findings + method always present."""
    runner = CliRunner()
    result = runner.invoke(
        main, ["test", "--prompt", "You are a helpful assistant.", "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "findings" in payload
    assert len(payload["findings"]) > 0
    assert "transparency" in payload
    assert payload["transparency"]["type"] == "deterministic_regex"
    assert payload["ruleset"] == RULESET_ID
    # At least one finding should carry a rule_id
    assert any(f.get("rule_id") for f in payload["findings"])


def test_test_human_shows_ruleset_and_method_without_explain_flag():
    runner = CliRunner()
    result = runner.invoke(
        main, ["test", "--prompt", "You are a helpful assistant."]
    )
    assert result.exit_code == 0, result.output
    assert RULESET_ID in result.output
    assert "crewscore rules" in result.output.lower() or "rules --json" in result.output
    # Findings visible by default (transparency)
    assert "missing" in result.output.lower() or "Findings" in result.output


def test_ruleset_id_is_0_4_0():
    """The ruleset moves alongside the package to 0.1.0.

    Versioned in lockstep with the package so any score can be traced back
    to the exact rules that produced it.
    """
    assert RULESET_ID == "crewscore-hygiene@0.1.0"


def test_changelog_does_not_reference_withdrawn_versions():
    """Every pre-0.1.0 build was withdrawn from PyPI.

    A changelog that tells readers "you are almost certainly coming from
    0.2.7" points at something nobody can install, and an upgrade section for
    a version that does not exist reads worse than no section at all.
    """
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    for gone in ("## [0.2.", "## [0.3.", "## [0.4."):
        assert gone not in changelog, gone + " is not an installable release"
    assert "withdrawn" in changelog.lower()
    assert "first supported release" in changelog.lower()

def test_pyproject_description_does_not_overclaim_production_readiness():
    """Packaging metadata must match what the tool actually does.

    docs/validation.md is the source of truth: the score does not establish
    production readiness. The description must not claim production-
    readiness assessment or certification.
    """
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    desc_line = next(
        line for line in text.splitlines() if line.strip().startswith("description")
    )
    lowered = desc_line.lower()
    assert "production-readiness" not in lowered
    assert "production readiness" not in lowered
    assert "certif" not in lowered
    # The description must say what the tool finds, in the words a
    # developer would use, without claiming it prevents any of it.
    assert "guardrails" in lowered or "failure modes" in lowered
    for promise in ("prevent", "protect", "secure your", "guarantee"):
        assert promise not in lowered, promise


def test_scoring_method_constant_honest():
    assert SCORING_METHOD["llm_calls"] is False
    assert "certification" in " ".join(SCORING_METHOD["what_this_is_not"]).lower()
    block = scoring_transparency_block()
    assert block["open_rules"].startswith("crewscore rules")


def _dim_score(matches, total):
    """The published per-dimension formula, restated independently."""
    if not total or matches == 0:
        return 0
    return min(100, round(15 + 85 * matches / total))


def test_a_prompt_stating_every_control_once_scores_below_the_lowest_tier():
    """docs/validation.md's central, self-contained proof.

    A prompt that states all eight governance controls clearly, once each,
    scores 28/100 -- under the lowest tier boundary of 50. Reaching 70 needs
    the same control restated 4-6 different ways, which is exactly the
    redundancy the Context Bloat detector calls a defect.

    This is the evidence the coverage-not-quality claim rests on, so it is
    pinned here: if a rule count changes, this number moves and the document
    must be updated with it.
    """
    from crewscore.scoring import overall_score

    per = {k: _dim_score(1, len(SCORER_MAP[k])) for k in DIMENSION_KEYS}
    assert overall_score(per) == 28, per
    twice = {k: _dim_score(2, len(SCORER_MAP[k])) for k in DIMENSION_KEYS}
    assert overall_score(twice) == 41, twice
    # The documented per-dimension range for a single clear statement.
    assert min(per.values()) == 24 and max(per.values()) == 32, per


def test_validation_doc_does_not_cite_the_withdrawn_corpus_statistics():
    """The corpus study was withdrawn after our own audit found impossible
    numbers in it (60% recall from n=2; a line total below its own minimum;
    a CI inconsistent with its p-value). Those figures must not survive
    anywhere, because a withdrawn statistic quoted in a summary table is
    still a published claim.
    """
    doc = Path("docs/validation.md").read_text(encoding="utf-8")
    withdrawn = ["+0.061", "0.863", "0.800", "+0.601", "p=0.36", "99.3%"]
    for stat in withdrawn:
        assert stat not in doc, stat + " is a withdrawn statistic"
    assert "withdrawn" in doc.lower()
