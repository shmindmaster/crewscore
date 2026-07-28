"""Synthetic corpus demo: discoverable, ordered gradient, honest framing."""

from pathlib import Path

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
    by_name = {Path(r["path"]).name: int(r["overall"]) for r in scored}
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
