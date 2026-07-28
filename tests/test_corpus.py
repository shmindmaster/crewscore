"""Synthetic corpus demo: discoverable, ordered gradient, honest framing."""

from pathlib import Path

from crewscore.profiles import CODING_AGENT_CONFIG
from crewscore.scan import discover_prompt_files, score_paths

REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "examples" / "corpus"


def test_corpus_prompts_discovered():
    files = discover_prompt_files(CORPUS)
    names = {p.name for p in files}
    assert "01-bare-assistant.md" in names
    assert "05-hardened-ops.md" in names
    assert len(files) >= 5


def test_corpus_score_gradient():
    """Bare fixtures score lower than partial; hardened is clearly higher."""
    scored = score_paths(discover_prompt_files(CORPUS))
    # Coding-agent config rows (the corpus AGENTS.md fixture) carry no
    # `overall` at all — they are judged on smells, not the governance score.
    by_name = {
        Path(r["path"]).name: int(r["overall"])
        for r in scored
        if r.get("governance_applicable", True)
    }
    assert by_name["01-bare-assistant.md"] == 0
    assert by_name["04-partial-hygiene.md"] > by_name["01-bare-assistant.md"]
    assert by_name["05-hardened-ops.md"] >= 70
    assert by_name["05-hardened-ops.md"] > by_name["04-partial-hygiene.md"]


def test_corpus_leaderboard_present():
    lb = CORPUS / "LEADERBOARD.md"
    assert lb.is_file()
    text = lb.read_text(encoding="utf-8")
    assert "crewscore-hygiene@" in text
    assert "structural" in text.lower()
    assert "not" in text.lower()


def test_agents_md_fixture_is_classified_as_coding_agent_config():
    """The corpus's own AGENTS.md-style fixture must be judged by the config
    ruleset, not handed a governance score. `classify_path()` matches exact
    basenames only, so the fixture must live at a real basename match
    (e.g. a subdirectory containing an actual AGENTS.md), not
    `prompts/03-agents-md-weak.md`.
    """
    files = discover_prompt_files(CORPUS)
    agents_md = [p for p in files if p.name == "AGENTS.md"]
    assert agents_md, "expected a real AGENTS.md fixture under examples/corpus"

    scored = score_paths(files)
    by_name = {Path(r["path"]).name: r for r in scored}
    result = by_name["AGENTS.md"]
    assert result["profile"] == CODING_AGENT_CONFIG
    assert result["governance_applicable"] is False
    assert result["tier"].startswith("CONFIG:")

    # The old misclassified path must be gone.
    assert not (CORPUS / "prompts" / "03-agents-md-weak.md").exists()


def test_leaderboard_shows_config_verdict_not_a_governance_grade():
    """LEADERBOARD.md must not present the AGENTS.md fixture as a scored
    (governed) row — that is the exact category error 0.3.1 exists to fix.
    """
    text = (CORPUS / "LEADERBOARD.md").read_text(encoding="utf-8")
    assert "03-agents-md-weak.md" not in text
    assert "CONFIG:" in text
