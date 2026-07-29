#!/usr/bin/env python3
"""Score examples/corpus/prompts and write LEADERBOARD.md (honest structural demo)."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from crewscore.scan import discover_prompt_files, score_paths  # noqa: E402
from crewscore.scoring import RULESET_ID  # noqa: E402


def main() -> int:
    corpus = ROOT / "examples" / "corpus"
    prompts = corpus / "prompts"
    if not prompts.is_dir():
        print(f"missing {prompts}", file=sys.stderr)
        return 1

    files = discover_prompt_files(corpus)
    if not files:
        print("no prompt files discovered under examples/corpus", file=sys.stderr)
        return 1

    scored = score_paths(files)
    # relative paths for stable display
    for item in scored:
        p = Path(item["path"])
        try:
            item["path"] = str(p.relative_to(corpus)).replace("\\", "/")
        except ValueError:
            item["path"] = p.name

    # Governed (system-prompt) rows rank by score; coding-agent config rows
    # are never handed a governance grade (see crewscore/profiles.py), so
    # they are listed separately rather than sorted into the same ranking.
    governed = [r for r in scored if r.get("governance_applicable", True)]
    config_rows = [r for r in scored if not r.get("governance_applicable", True)]
    governed_sorted = sorted(governed, key=lambda r: (int(r["overall"]), r["path"]))

    lines = [
        "# CrewScore corpus leaderboard",
        "",
        "Synthetic fixtures representing common agent-prompt shapes "
        "(bare demo → partial hygiene → hardened ops). "
        "**Structural scores only** — not red-team results, not runtime proof.",
        "",
        "> **These are fixtures, not evidence.** They were written to exercise "
        "the rules, which is why the top one scores well. The reproducible "
        "public validation corpus contains 356 prompts (83 production-agent "
        "and 273 general-purpose); it supports coverage observations, not a "
        "quality ranking. Read [`docs/validation.md`](../../docs/validation.md) "
        "before reading anything into a number here.",
        "",
        f"- **Ruleset:** `{RULESET_ID}`",
        f"- **Generated:** {date.today().isoformat()}",
        f"- **Command:** `crewscore scan examples/corpus`",
        f"- **Regenerate:** `python scripts/score_corpus.py`",
        "",
        "| Rank | Path | Score | Tier |",
        "| ---: | --- | ---: | --- |",
    ]
    for i, row in enumerate(reversed(governed_sorted), start=1):
        lines.append(
            f"| {i} | `{row['path']}` | **{row['overall']}** | `{row['tier']}` |"
        )

    if config_rows:
        lines.extend(
            [
                "",
                "### Coding-agent config (no governance grade)",
                "",
                "These files are repo guidance for a coding agent, not a "
                "production system prompt — they are judged on configuration "
                "smells, never the governance score. See "
                "[configuration smells](../../README.md#configuration-smells).",
                "",
                "| Path | Verdict |",
                "| --- | --- |",
            ]
        )
        for row in sorted(config_rows, key=lambda r: r["path"]):
            lines.append(f"| `{row['path']}` | `{row['tier']}` |")

    lines.extend(
        [
            "",
            "## How to reproduce",
            "",
            "```bash",
            "pip install crewscore",
            "crewscore scan examples/corpus",
            "crewscore scan examples/corpus --json",
            "crewscore test --prompt-file examples/corpus/prompts/01-bare-assistant.md --explain",
            "```",
            "",
            "## Takeaway",
            "",
            "Bare demo agents score near zero on production hygiene signals. "
            "Adding explicit injection/hallucination/human-gate language raises "
            "the structural score. That is a **pre-gate**, not certification — "
            "pair with Promptfoo/garak for live eval.",
            "",
        ]
    )

    out = corpus / "LEADERBOARD.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out)
    print(json.dumps(scored, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
