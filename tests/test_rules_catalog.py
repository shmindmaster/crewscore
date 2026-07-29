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
from crewscore.scorers.structural_analysis import CONCEPTS, SCORER_MAP
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
    formula = payload["method"]["dimension_score_formula"]
    assert "matches" in formula
    # The denominator is controls, not rules. If this reverts to counting rules
    # the published formula silently starts rewarding synonyms again.
    assert "control" in formula
    assert "structural_analysis.py" in payload["method"]["source_of_truth"]
    assert payload["rule_count"] == len(list_rules())


def test_demo_formula_matches_documented_math():
    """`(100 * matches + N // 2) // N`, exactly as published — including the
    rounding, which must be half-up so the browser engine can match it."""
    assert demo_formula(0, 8) == 0
    assert demo_formula(4, 4) == 100
    assert demo_formula(1, 3) == 33
    assert demo_formula(2, 3) == 67
    assert demo_formula(1, 2) == 50
    # Half-up, not Python's default half-to-even: round(12.5) is 12, and a
    # browser scoring 13 for the same prompt is the divergence this prevents.
    assert demo_formula(1, 8) == 13
    assert demo_formula(0, 0) == 0


def test_no_control_is_worth_more_than_any_other_in_its_dimension():
    """Equal weight is a published property, not an accident of the grouping."""
    from crewscore.rules_catalog import list_concepts

    by_dim: dict[str, set[int]] = {}
    for row in list_concepts():
        by_dim.setdefault(row["dimension"], set()).add(row["points"])
    for dimension, points in by_dim.items():
        assert len(points) == 1, f"{dimension} weights controls unequally: {points}"


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


def test_ruleset_id_is_0_5_0():
    """The ruleset remains at 0.5.0 while package 0.6.0 adds policy tooling.

    Versioned in lockstep with the package so any score can be traced back
    to the exact rules that produced it.
    """
    assert RULESET_ID == "crewscore-hygiene@0.5.0"


def test_changelog_does_not_reference_withdrawn_versions():
    """Every pre-0.1.0 build was withdrawn from PyPI.

    A changelog that tells readers "you are almost certainly coming from
    0.2.7" points at something nobody can install, and an upgrade section for
    a version that does not exist reads worse than no section at all.
    """
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    # 0.2.x and 0.4.0 were published and then deleted. PyPI never lets a
    # deleted version number be re-used, so those numbers are burned for good
    # and no future release may claim one - which is why the scoring release
    # is 0.3.0 and not the 0.2.0 a minor bump from 0.1.0 would suggest.
    for gone in ("## [0.2.", "## [0.4."):
        assert gone not in changelog, gone + " is a burned version number"
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


def _dim_score(covered, total):
    """The published per-dimension formula, restated independently."""
    if not total or covered == 0:
        return 0
    return (100 * covered + total // 2) // total


def test_the_whole_scale_is_reachable_by_a_well_written_prompt():
    """docs/validation.md's central, self-contained proof.

    Until ruleset 0.2.0 a dimension scored `matched_rules / total_rules`, where
    the rules inside a dimension are near-synonyms. A prompt that stated all
    eight controls clearly, once each, scored 28/100 -- under the lowest tier
    boundary of 50 -- and reaching 70 took the same control restated 4-6 ways,
    the exact redundancy the Context Bloat detector calls a defect. A metric a
    well-written prompt could not pass was not measuring quality.

    Counting controls instead of synonyms fixes it: covering every control in
    a dimension scores 100 there, so the top of the scale is reachable by
    writing well rather than by writing more.
    """
    from crewscore.scoring import overall_score

    full = {k: _dim_score(len(CONCEPTS[k]), len(CONCEPTS[k])) for k in DIMENSION_KEYS}
    assert overall_score(full) == 100, full

    # Half the controls in every dimension lands mid-scale, not at the floor.
    half = {
        k: _dim_score(len(CONCEPTS[k]) // 2, len(CONCEPTS[k])) for k in DIMENSION_KEYS
    }
    assert 30 <= overall_score(half) <= 60, half

    # No dimension is stuck below the lowest tier when fully covered - that was
    # the defect, and it was invisible until someone did the arithmetic.
    assert min(full.values()) == 100, full


def test_stating_one_control_many_ways_cannot_beat_stating_two_controls():
    """The anti-bloat invariant, at the level of the published formula."""
    for dimension in DIMENSION_KEYS:
        total = len(CONCEPTS[dimension])
        if total < 2:
            continue
        assert _dim_score(1, total) < _dim_score(2, total), dimension


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
