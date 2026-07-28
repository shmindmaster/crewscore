"""Manifest checks for the official CrewScore GitHub Action."""

from pathlib import Path


def test_action_yml_present():
    text = Path("action.yml").read_text(encoding="utf-8")
    assert "prompt-file" in text
    assert "threshold" in text
    assert "crewscore" in text.lower()
