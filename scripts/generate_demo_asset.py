#!/usr/bin/env python3
"""Generate docs/demo.svg from the canonical demo fixture and current scorer."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from crewscore.hero import hero_missing_control
from crewscore.scorers.structural_analysis import analyze_with_findings

ROOT = Path(__file__).resolve().parents[1]
DEMO_FIXTURE = ROOT / "assets" / "demo-fixture.js"
DEMO_SVG = ROOT / "docs" / "demo.svg"

PROMPT_RE = re.compile(r"\n  prompt: `(?P<prompt>.*?)`,\n", re.DOTALL)

BEFORE_TEXT = "Fictional Northstar Clinic fixture"
AFTER_TEXT = "same fixture + human approval"
MISSING_COUNT_WORDS = {
    0: "No",
    1: "One",
    2: "Two",
    3: "Three",
    4: "Four",
    5: "Five",
    6: "Six",
    7: "Seven",
    8: "Eight",
    9: "Nine",
    10: "Ten",
    11: "Eleven",
    12: "Twelve",
    13: "Thirteen",
    14: "Fourteen",
    15: "Fifteen",
    16: "Sixteen",
    17: "Seventeen",
    18: "Eighteen",
    19: "Nineteen",
    20: "Twenty",
    21: "Twenty-one",
    22: "Twenty-two",
    23: "Twenty-three",
}


def _fixture_prompt() -> str:
    text = DEMO_FIXTURE.read_text(encoding="utf-8")
    match = PROMPT_RE.search(text)
    if not match:
        raise RuntimeError("could not locate prompt in assets/demo-fixture.js")
    return match.group("prompt")


def _analyze(prompt: str) -> tuple[int, int, str]:
    dimensions, findings = analyze_with_findings(prompt)
    matched = sum(1 for f in findings if f.get("status") == "matched")
    total = len(findings)
    hero = hero_missing_control(findings)
    gap = (
        hero.get("pattern_or_reason")
        if hero
        else None
    ) or "All published controls were detected."
    if not gap and hero:
        gap = hero.get("label") or hero.get("reason") or "All published controls were detected."
    return matched, total, gap


def _missing_text(remaining: int) -> str:
    return f"{MISSING_COUNT_WORDS.get(remaining, str(remaining))} controls may be missing. Low coverage is actionable."


def _render_svg(before: int, after: int, total: int, gap: str) -> str:
    before_track = 360
    after_fill = round(before_track * after / max(1, total))
    after_bar = round(before_track * after / max(1, total))
    before_bar = before_track
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540" role="img" aria-labelledby="title desc">
  <title id="title">CrewScore — written control coverage</title>
  <desc id="desc">The fictional Northstar Clinic demo fixture covers {before} of {total} published controls. After adding the selected human-approval wording, coverage rises to {after} of {total}. Coverage is not runtime proof.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0E1612"/>
      <stop offset="100%" stop-color="#15241C"/>
    </linearGradient>
    <style>
      .t {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; fill: #EEF4EF; }}
      .muted {{ fill: #B1BCB4; }}
      .mint {{ fill: #6FDAA6; }}
      .warn {{ fill: #EDCC7A; }}
      .mono {{ font-family: ui-monospace, Consolas, monospace; }}
    </style>
  </defs>
  <rect width="960" height="540" fill="url(#bg)"/>
  <!-- brand mark -->
  <rect x="48" y="40" width="44" height="44" rx="12" fill="#0B4F33"/>
  <rect x="58" y="50" width="24" height="5" rx="2.5" fill="#173F2B"/>
  <rect x="58" y="50" width="18" height="5" rx="2.5" fill="#6FDAA6"/>
  <rect x="58" y="59" width="24" height="5" rx="2.5" fill="#173F2B"/>
  <rect x="58" y="59" width="12" height="5" rx="2.5" fill="#A3EDC4"/>
  <rect x="58" y="68" width="24" height="5" rx="2.5" fill="#173F2B"/>
  <rect x="58" y="68" width="7" height="5" rx="2.5" fill="#6FDAA6"/>
  <text class="t" x="106" y="70" font-size="26" font-weight="800">CrewScore</text>
  <text class="t muted" x="48" y="112" font-size="16">Written-control coverage · not runtime proof</text>

  <!-- before panel -->
  <rect x="48" y="140" width="420" height="300" rx="18" fill="#17201B" stroke="#405147"/>
  <text class="t muted" x="72" y="178" font-size="14" font-weight="700">BEFORE</text>
  <text class="t mono muted" x="72" y="208" font-size="13">"{BEFORE_TEXT}"</text>
  <text class="t" x="72" y="280" font-size="64" font-weight="800">{before}<span class="muted" font-size="32"> / {total}</span></text>
  <text class="t muted" x="72" y="318" font-size="16">written controls found</text>
  <rect x="72" y="340" width="{before_bar}" height="12" rx="6" fill="#202B24"/>
  <text class="t warn" x="72" y="390" font-size="15" font-weight="700">First gap to review: human_gate.approval_required — {gap}</text>
  <text class="t muted" x="72" y="416" font-size="13">{_missing_text(total - before)}</text>

  <!-- after panel -->
  <rect x="492" y="140" width="420" height="300" rx="18" fill="#17201B" stroke="#6FDAA6" stroke-opacity="0.45"/>
  <text class="t mint" x="516" y="178" font-size="14" font-weight="700">AFTER · selected wording added</text>
  <text class="t mono muted" x="516" y="208" font-size="13">{AFTER_TEXT}</text>
  <text class="t mint" x="516" y="280" font-size="64" font-weight="800">{after}<span class="muted" font-size="32"> / {total}</span></text>
  <text class="t muted" x="516" y="318" font-size="16">written controls found</text>
  <rect x="516" y="340" width="{before_track}" height="12" rx="6" fill="#202B24"/>
  <rect x="516" y="340" width="{after_bar}" height="12" rx="6" fill="#6FDAA6"/>
  <text class="t muted" x="516" y="390" font-size="15">Text is present. Still not proof the agent obeys it.</text>
  <text class="t muted" x="516" y="416" font-size="13">crewscore.ai · pip install crewscore</text>

  <text class="t muted" x="48" y="500" font-size="14">{total} public controls · offline · no API key · open rules</text>
</svg>
"""


def generate(output: Path) -> None:
    before_prompt = _fixture_prompt()
    after_prompt = f"{before_prompt}\nA human must approve."
    before, total, gap = _analyze(before_prompt)
    after, _, _ = _analyze(after_prompt)
    if total != 23:
        raise RuntimeError(f"expected 23 controls, found {total}")
    if before != 8 or after != 9:
        raise RuntimeError(f"unexpected fixture score contract: {before}/{total} to {after}/{total}")
    if not gap:
        raise RuntimeError("fixture first gap could not be resolved")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_render_svg(before, after, total, gap), encoding="utf-8")
    os.utime(output, None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEMO_SVG, help="Target demo SVG path")
    args = parser.parse_args()

    generate(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
