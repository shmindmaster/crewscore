"""Transparency: open rules catalog is complete and non-black-box."""

import json

from click.testing import CliRunner

from crewscore.cli import main
from crewscore.rules_catalog import (
    SCORING_METHOD,
    catalog_payload,
    demo_formula,
    list_rules,
    scoring_transparency_block,
)
from crewscore.scorers.structural_analysis import SCORER_MAP
from crewscore.scoring import RULESET_ID


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


def test_scoring_method_constant_honest():
    assert SCORING_METHOD["llm_calls"] is False
    assert "certification" in " ".join(SCORING_METHOD["what_this_is_not"]).lower()
    block = scoring_transparency_block()
    assert block["open_rules"].startswith("crewscore rules")
