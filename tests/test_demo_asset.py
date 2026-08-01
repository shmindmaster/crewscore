"""The README hero image is a published claim, so hold it to the same bar as
the corpus report: every number in `docs/demo.svg` must be reproducible by
running the shipped scorer, not typed by hand.

The canonical fixture is the Northstar Clinic example. It starts at 8/23 and
adds one control with a deterministic human-approval phrase.
"""

from __future__ import annotations

import os
import tempfile
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DEMO_SVG = REPO / "docs" / "demo.svg"
DEMO_SCRIPT = REPO / "scripts" / "generate_demo_asset.py"
FIXTURE_JS = REPO / "assets" / "demo-fixture.js"
FIXTURE_PROMPT_RE = re.compile(r"\n  prompt: `(?P<prompt>.*?)`,\n", re.DOTALL)

COVERAGE_RE = re.compile(r"CONTROL COVERAGE:\s+(\d+)/(\d+) written")
FIRST_GAP_RE = re.compile(r"FIRST GAP TO REVIEW:\s+(.+)")


def _cli(*args: str) -> str:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    proc = subprocess.run(
        [sys.executable, "-m", "crewscore", *args],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    assert proc.returncode in (0, 1, 2), proc.stdout + proc.stderr
    return proc.stdout


def _fixture_prompt() -> str:
    fixture = FIXTURE_PROMPT_RE.search(FIXTURE_JS.read_text(encoding="utf-8"))
    assert fixture, "could not read the public demo fixture prompt"
    return fixture.group("prompt")


def _generate_demo_svg(output: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(DEMO_SCRIPT), "--output", str(output)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def _coverage(prompt_text: str) -> tuple[int, int]:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8", delete=False) as handle:
        handle.write(prompt_text)
        path = handle.name
    match = COVERAGE_RE.search(_cli("test", "--prompt-file", path))
    assert match, "scorer did not print a coverage line"
    Path(path).unlink(missing_ok=True)
    return int(match.group(1)), int(match.group(2))


def _first_gap(prompt_text: str) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8", delete=False) as handle:
        handle.write(prompt_text)
        path = handle.name
    gap = FIRST_GAP_RE.search(_cli("test", "--prompt-file", path))
    assert gap, "scorer did not name a first gap for the demo fixture"
    Path(path).unlink(missing_ok=True)
    return gap.group(1).strip()


@pytest.fixture(scope="module")
def measured() -> dict[str, object]:
    before_prompt = _fixture_prompt()
    before, total = _coverage(before_prompt)
    before_gap = _first_gap(before_prompt)
    after_prompt = f"{before_prompt}\nA human must approve."
    after, after_total = _coverage(after_prompt)
    assert total == after_total
    return {
        "before": before,
        "after": after,
        "total": total,
        "first_gap": before_gap,
    }


def _svg_panel_number(svg: str, anchor_x: str) -> int:
    match = re.search(rf'<text[^>]*x="{anchor_x}"[^>]*font-size="64"[^>]*>(\d+)', svg)
    assert match, f"no 64px headline number anchored at x={anchor_x}"
    return int(match.group(1))


def test_demo_svg_is_source_generated(measured, tmp_path):
    generated = tmp_path / "demo.svg"
    _generate_demo_svg(generated)
    assert generated.exists()
    assert generated.read_text(encoding="utf-8") == DEMO_SVG.read_text(encoding="utf-8")


def test_demo_svg_before_number_is_reproducible(measured):
    svg = DEMO_SVG.read_text(encoding="utf-8")
    assert _svg_panel_number(svg, "72") == measured["before"]


def test_demo_svg_after_number_is_reproducible(measured):
    svg = DEMO_SVG.read_text(encoding="utf-8")
    assert _svg_panel_number(svg, "516") == measured["after"], (
        "docs/demo.svg does not match the selected fixture wording"
    )


def test_demo_svg_control_total_matches_the_ruleset(measured):
    svg = DEMO_SVG.read_text(encoding="utf-8")
    assert svg.count(f"/ {measured['total']}") == 2


def test_demo_svg_names_the_gap_the_scorer_names(measured):
    svg = DEMO_SVG.read_text(encoding="utf-8")
    assert measured["first_gap"] in svg, (
        f"demo.svg must cite the scorer's actual first gap: {measured['first_gap']!r}"
    )


def test_demo_svg_uses_the_current_label():
    svg = DEMO_SVG.read_text(encoding="utf-8").lower()
    assert "biggest gap" not in svg
    assert "first gap to review" in svg


def test_demo_svg_progress_bar_matches_its_own_number(measured):
    svg = DEMO_SVG.read_text(encoding="utf-8")
    track = re.search(r'<rect x="516" y="340" width="(\d+)"[^>]*fill="#202B24"', svg)
    fill = re.search(r'<rect x="516" y="340" width="(\d+)"[^>]*fill="#6FDAA6"', svg)
    assert track and fill

    expected = round(int(track.group(1)) * measured["after"] / measured["total"])
    assert abs(int(fill.group(1)) - expected) <= 2


def test_demo_svg_keeps_the_not_runtime_proof_caveat():
    svg = DEMO_SVG.read_text(encoding="utf-8").lower()
    assert "not runtime proof" in svg
