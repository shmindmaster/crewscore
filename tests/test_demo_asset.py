"""The README hero image is a published claim, so hold it to the same bar as
the corpus report: every number in `docs/demo.svg` must be reproducible by
running the shipped scorer, not typed by hand.

This exists because it was not true. `demo.svg` claimed a bare assistant prompt
reaches 14/23 after `crewscore fix` when the tool actually produces 13/23, and
it kept the retired "Biggest gap" label after the 0.6.4 rename. Both survived
review because nothing executed the picture. The published hero now uses the
canonical fictional 8-to-9 browser-demo fixture instead.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DEMO_SVG = REPO / "docs" / "demo.svg"

# The public fixture is JavaScript, but its prompt is a plain template literal.
FIXTURE_JS = REPO / "assets" / "demo-fixture.js"
FIXTURE_PROMPT_RE = re.compile(r"\n  prompt: `(?P<prompt>.*?)`,\n", re.DOTALL)

COVERAGE_RE = re.compile(r"CONTROL COVERAGE:\s+(\d+)/(\d+) written")
FIRST_GAP_RE = re.compile(r"FIRST GAP TO REVIEW:\s+(.+)")


def _cli(*args: str) -> str:
    # The report draws box-glyphs; force UTF-8 both ways so a cp1252 console
    # (Windows default) does not turn a real assertion into a decode error.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    proc = subprocess.run(
        [sys.executable, "-m", "crewscore", *args],
        cwd=str(REPO), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env,
    )
    assert proc.returncode in (0, 1, 2), proc.stdout + proc.stderr
    return proc.stdout


def _coverage(prompt_file: Path) -> tuple[int, int]:
    match = COVERAGE_RE.search(_cli("test", "--prompt-file", str(prompt_file)))
    assert match, "scorer did not print a coverage line"
    return int(match.group(1)), int(match.group(2))


def _svg_panel_number(svg: str, anchor_x: str) -> int:
    """The big N in the panel whose text elements are anchored at `anchor_x`."""
    match = re.search(
        rf'<text[^>]*x="{anchor_x}"[^>]*font-size="64"[^>]*>(\d+)', svg
    )
    assert match, f"no 64px headline number anchored at x={anchor_x}"
    return int(match.group(1))


@pytest.fixture(scope="module")
def measured(tmp_path_factory) -> dict[str, object]:
    """Score the public demo fixture before and after its selected wording."""
    work = tmp_path_factory.mktemp("demo")
    before = work / "before.md"
    fixture = FIXTURE_PROMPT_RE.search(FIXTURE_JS.read_text(encoding="utf-8"))
    assert fixture, "could not read the public demo fixture prompt"
    before.write_text(fixture.group("prompt"), encoding="utf-8")
    after = work / "after.md"

    before_matched, total = _coverage(before)
    gap = FIRST_GAP_RE.search(_cli("test", "--prompt-file", str(before)))
    assert gap, "scorer did not name a first gap for the demo fixture"

    after.write_text(
        f"{before.read_text(encoding='utf-8')}\nA human must approve.",
        encoding="utf-8",
    )
    after_matched, after_total = _coverage(after)
    assert total == after_total, "control total changed between runs"

    return {
        "before": before_matched,
        "after": after_matched,
        "total": total,
        "first_gap": gap.group(1).strip(),
    }


def test_demo_svg_before_number_is_reproducible(measured):
    svg = DEMO_SVG.read_text(encoding="utf-8")
    assert _svg_panel_number(svg, "72") == measured["before"]


def test_demo_svg_after_number_is_reproducible(measured):
    """The published hero must match the selected fixture wording."""
    svg = DEMO_SVG.read_text(encoding="utf-8")
    assert _svg_panel_number(svg, "516") == measured["after"], (
        "docs/demo.svg does not match the selected fixture wording"
    )


def test_demo_svg_control_total_matches_the_ruleset(measured):
    svg = DEMO_SVG.read_text(encoding="utf-8")
    assert svg.count(f"/ {measured['total']}") == 2, (
        f"both panels must denominate in the shipped total ({measured['total']})"
    )


def test_demo_svg_names_the_gap_the_scorer_names(measured):
    svg = DEMO_SVG.read_text(encoding="utf-8")
    assert measured["first_gap"] in svg, (
        f"demo.svg must cite the scorer's actual first gap: {measured['first_gap']!r}"
    )


def test_demo_svg_uses_the_current_label():
    """0.6.4 renamed "biggest gap" — it implied a risk ranking the tool does
    not do. The picture is a surface like any other."""
    svg = DEMO_SVG.read_text(encoding="utf-8").lower()
    assert "biggest gap" not in svg
    assert "first gap to review" in svg


def test_demo_svg_progress_bar_matches_its_own_number(measured):
    """A bar wider than the score reads as a bigger win than the tool delivers."""
    svg = DEMO_SVG.read_text(encoding="utf-8")
    track = re.search(r'<rect x="516" y="340" width="(\d+)"[^>]*fill="#202B24"', svg)
    fill = re.search(r'<rect x="516" y="340" width="(\d+)"[^>]*fill="#6FDAA6"', svg)
    assert track and fill, "after-panel bar track/fill not found"

    expected = round(int(track.group(1)) * measured["after"] / measured["total"])
    assert abs(int(fill.group(1)) - expected) <= 2, (
        f"fill {fill.group(1)}px should be ~{expected}px for "
        f"{measured['after']}/{measured['total']}"
    )


def test_demo_svg_keeps_the_not_runtime_proof_caveat():
    svg = DEMO_SVG.read_text(encoding="utf-8").lower()
    assert "not proof the agent obeys it" in svg or "not runtime proof" in svg
