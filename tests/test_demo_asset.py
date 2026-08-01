"""The README hero image is a published claim, so hold it to the same bar as
the corpus report: every number in `docs/demo.svg` must be reproducible by
running the shipped scorer, not typed by hand.

The canonical fixture is the Northstar Clinic example. It starts at 8/23 and
adds one control with a deterministic human-approval phrase.
"""

from __future__ import annotations

import json
import hashlib
import os
import re
import tempfile
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Any

import pytest

EXPECTED_DEMO_SHA256 = "9e274ac414f89ed210edc2d5266ddf8a2ff7d712652f01bf8609fce648c8ec8b"

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
    payload = json.loads(_cli("test", "--prompt-file", path, "--json"))
    hero = payload.get("coverage", {}).get("hero") or {}
    concept = hero.get("concept")
    label = hero.get("label") or hero.get("pattern_or_reason")
    assert concept, "scorer missing first gap concept"
    assert label, "scorer missing first gap label"
    Path(path).unlink(missing_ok=True)
    return f"{concept} — {label}"


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
        "first_gap_concept": before_gap.partition(" — ")[0],
        "first_gap_label": before_gap.partition(" — ")[2],
    }


def _svg_panel_number(svg: str, anchor_x: str) -> int:
    match = re.search(rf'<tspan[^>]*x="{anchor_x}"[^>]*font-size="64"[^>]*>(\d+)</tspan>', svg)
    assert match, f"no 64px headline number anchored at x={anchor_x}"
    return int(match.group(1))


def _first_gap_block(svg: str) -> str:
    candidates = re.findall(
        r'<text[^>]*>.*?</text>',
        svg,
        re.DOTALL,
    )
    for candidate in candidates:
        if 'class="t warn" x="72" y="382"' in candidate:
            return candidate
    raise AssertionError("could not locate first-gap block")


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
    measured_gap = measured["first_gap"]
    concept, _, detail = measured_gap.partition(" — ")
    assert concept in svg, (
        f"demo.svg missing first-gap concept: {concept!r}"
    )
    if detail:
        text_only = re.sub(r"<[^>]+>", " ", svg)
        assert all(word in text_only for word in detail.split()), f"demo.svg missing first-gap detail: {detail!r}"


def test_demo_svg_uses_the_current_label():
    svg = DEMO_SVG.read_text(encoding="utf-8").lower()
    assert "biggest gap" not in svg
    assert "controls may be missing" in svg


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


def test_demo_svg_gap_label_is_wrapped_into_text_runs(measured):
    svg = DEMO_SVG.read_text(encoding="utf-8")
    block = _first_gap_block(svg)
    tspans = re.findall(r"<tspan[^>]*>(.*?)</tspan>", block)
    if tspans:
        assert tspans[0].strip()
        assert all(len(line.strip()) <= 40 for line in tspans), "first-gap lines must not overflow wrap budget"
    else:
        assert len(block.strip()) <= 58
    if len(measured["first_gap"]) > 40:
        assert len(tspans) >= 2


def _rendered_svg_text_nodes(svg_path: Path) -> dict[str, Any]:
    if not shutil.which("node"):
        pytest.skip("node not installed; skipping browser layout assertions")
    proc = subprocess.run(
        [
            "node",
            "-e",
            """
const fs = require("fs");
const { chromium } = require("playwright");

(async () => {
  const svg = fs.readFileSync(process.argv[1], "utf8");
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const dataUrl = `data:image/svg+xml;base64,${Buffer.from(svg, "utf8").toString("base64")}`;
  await page.goto(dataUrl);
  const result = await page.evaluate(() => {
    const svg = document.querySelector("svg");
    if (!svg) return { violations: [{ node: "missing-svg" }], text: [], nodeCount: 0 };
    const panels = [
      { name: "before", x: 48, y: 140, width: 420, height: 300 },
      { name: "after", x: 492, y: 140, width: 420, height: 300 },
    ];
    const violations = [];
    const nodes = [...svg.querySelectorAll("text,tspan")];
    for (const node of nodes) {
      const box = node.getBBox();
      if (box.width === 0 || box.height === 0) {
        continue;
      }
      const cx = box.x + box.width / 2;
      const cy = box.y + box.height / 2;
      const panel = cy >= 140 && cy <= 440
        ? (cx < 486 ? panels[0] : panels[1])
        : null;
      if (!panel) {
        continue;
      }
      if (box.x < panel.x || box.x + box.width > panel.x + panel.width || box.y < panel.y || box.y + box.height > panel.y + panel.height) {
        violations.push({
          node: node.tagName,
          x: box.x,
          y: box.y,
          width: box.width,
          height: box.height,
          panel: panel.name,
        });
      }
    }
    return {
      violations,
      text: nodes.map((node) => (node.textContent || "").trim()).filter(Boolean),
      nodeCount: nodes.length,
    };
  });
  await browser.close();
  process.stdout.write(JSON.stringify(result));
})().catch((error) => {
  process.stderr.write(String(error));
  process.exit(1);
});
""",
            str(svg_path),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def test_demo_svg_gap_panel_layout_stays_within_panels():
    rendered = _rendered_svg_text_nodes(DEMO_SVG)
    assert rendered["violations"] == []
    assert rendered["nodeCount"] >= 20
    joined = " ".join(rendered["text"])
    assert "8 / 23" in joined
    assert "9 / 23" in joined
    assert "human_gate.approval_required" in joined


def test_demo_svg_uses_canonical_lf_utf8_bytes():
    payload = DEMO_SVG.read_bytes()
    assert b"\r\n" not in payload
    assert b"<span" not in payload
    payload.decode("utf-8")
    assert hashlib.sha256(payload).hexdigest() == EXPECTED_DEMO_SHA256
