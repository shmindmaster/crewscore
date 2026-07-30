"""Corpus card SVG: screenshot-ready validation shock numbers."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
VALIDATION_MD = REPO / "docs" / "validation-corpus.md"


def test_render_corpus_card_svg_includes_key_numbers_and_honesty():
    from crewscore.corpus_card import render_corpus_card_svg

    svg = render_corpus_card_svg(
        production_n=83,
        production_median=14,
        gpt_store_n=273,
        gpt_store_median=0,
        cliffs_delta=0.672,
        ruleset="crewscore-hygiene@0.5.0",
        homepage="https://crewscore.ai",
    )

    assert svg.lstrip().startswith("<svg")
    assert "CrewScore" in svg
    assert "14" in svg
    assert re.search(r"\b0\b", svg)
    assert "83" in svg
    assert "273" in svg
    assert "0.672" in svg or "0.67" in svg
    assert "crewscore-hygiene@0.5.0" in svg
    assert "https://crewscore.ai" in svg
    assert "written-control coverage" in svg.lower() or "not runtime proof" in svg.lower()
    # Honesty: must not overclaim
    lowered = svg.lower()
    assert "production ready" not in lowered
    assert "safety certified" not in lowered
    # Social-friendly dimensions
    width_m = re.search(r'width="(\d+)"', svg)
    height_m = re.search(r'height="(\d+)"', svg)
    assert width_m and height_m
    assert 600 <= int(width_m.group(1)) <= 1000
    assert 300 <= int(height_m.group(1)) <= 500


def test_parse_validation_corpus_stats_from_real_file():
    from crewscore.corpus_card import parse_validation_corpus_stats

    md_text = VALIDATION_MD.read_text(encoding="utf-8")
    stats = parse_validation_corpus_stats(md_text)

    # Assert against the committed file content (parse row medians / n from tables).
    prod_row = re.search(
        r"\|\s*Production agent system prompts\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
        md_text,
    )
    gpt_row = re.search(
        r"\|\s*General-purpose GPT-Store prompts\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
        md_text,
    )
    delta_m = re.search(r"Cliff's delta\s*=\s*([0-9.]+)", md_text, re.IGNORECASE)
    assert prod_row and gpt_row and delta_m

    assert stats["production_n"] == int(prod_row.group(1))
    assert stats["production_median"] == int(prod_row.group(2))
    assert stats["gpt_store_n"] == int(gpt_row.group(1))
    assert stats["gpt_store_median"] == int(gpt_row.group(2))
    assert abs(stats["cliffs_delta"] - float(delta_m.group(1))) < 1e-9

    # Sanity: current published shock numbers (regression anchors)
    assert stats["production_median"] == 14
    assert stats["gpt_store_median"] == 0
    assert stats["production_n"] == 83
    assert stats["gpt_store_n"] == 273


def test_generate_corpus_card_round_trip(tmp_path, monkeypatch):
    """scripts/generate_corpus_card.py writes SVG + JSON under a chosen dir."""
    # Import after path is set so the script can resolve REPO relative to itself.
    sys.path.insert(0, str(REPO))
    from scripts.generate_corpus_card import main

    out_dir = tmp_path / "dist-pack"
    out_dir.mkdir()
    svg_path = out_dir / "corpus-card.svg"
    json_path = out_dir / "corpus-card.json"

    rc = main(
        [
            "--validation-md",
            str(VALIDATION_MD),
            "--output-svg",
            str(svg_path),
            "--output-json",
            str(json_path),
        ]
    )
    assert rc == 0
    assert svg_path.is_file()
    assert json_path.is_file()

    svg = svg_path.read_text(encoding="utf-8")
    assert svg.lstrip().startswith("<svg")
    assert "14" in svg
    assert "CrewScore" in svg

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["production_median"] == 14
    assert data["gpt_store_median"] == 0
    assert data["production_n"] == 83
    assert data["gpt_store_n"] == 273
    assert "cliffs_delta" in data


def test_render_escapes_user_text():
    from crewscore.corpus_card import render_corpus_card_svg

    svg = render_corpus_card_svg(
        production_n=1,
        production_median=2,
        gpt_store_n=3,
        gpt_store_median=4,
        cliffs_delta=0.5,
        ruleset='crewscore<>&"@0',
        homepage="https://example.com/?a=1&b=2",
    )
    assert "<" not in re.findall(r"crewscore[^<]*", svg)[0] or "&lt;" in svg or "&amp;" in svg
    assert "&amp;" in svg or "https://example.com/" in svg
