#!/usr/bin/env python3
"""Generate the public corpus card SVG + JSON from docs/validation-corpus.md.

    py scripts/generate_corpus_card.py

Writes docs/dist-pack/corpus-card.svg and docs/dist-pack/corpus-card.json.
No network. Safe to regenerate after a validation re-run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from crewscore.corpus_card import (  # noqa: E402
    parse_validation_corpus_stats,
    render_corpus_card_svg,
)
from crewscore.scoring import RULESET_ID  # noqa: E402

DEFAULT_MD = ROOT / "docs" / "validation-corpus.md"
DEFAULT_SVG = ROOT / "docs" / "dist-pack" / "corpus-card.svg"
DEFAULT_JSON = ROOT / "docs" / "dist-pack" / "corpus-card.json"
HOMEPAGE = "https://crewscore.ai"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render CrewScore corpus card SVG from validation-corpus.md"
    )
    parser.add_argument(
        "--validation-md",
        type=Path,
        default=DEFAULT_MD,
        help="Path to validation-corpus.md",
    )
    parser.add_argument(
        "--output-svg",
        type=Path,
        default=DEFAULT_SVG,
        help="Where to write corpus-card.svg",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_JSON,
        help="Where to write corpus-card.json",
    )
    parser.add_argument(
        "--ruleset",
        default=RULESET_ID,
        help="Ruleset id printed on the card",
    )
    parser.add_argument(
        "--homepage",
        default=HOMEPAGE,
        help="Homepage URL printed on the card",
    )
    args = parser.parse_args(argv)

    md_path: Path = args.validation_md
    if not md_path.is_file():
        print(f"error: validation markdown not found: {md_path}", file=sys.stderr)
        return 1

    md_text = md_path.read_text(encoding="utf-8")
    stats = parse_validation_corpus_stats(md_text)

    svg = render_corpus_card_svg(
        production_n=stats["production_n"],
        production_median=stats["production_median"],
        gpt_store_n=stats["gpt_store_n"],
        gpt_store_median=stats["gpt_store_median"],
        cliffs_delta=stats["cliffs_delta"],
        ruleset=args.ruleset,
        homepage=args.homepage,
    )

    try:
        source_rel = md_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        source_rel = md_path.as_posix()

    payload = {
        "production_n": stats["production_n"],
        "production_median": stats["production_median"],
        "gpt_store_n": stats["gpt_store_n"],
        "gpt_store_median": stats["gpt_store_median"],
        "cliffs_delta": stats["cliffs_delta"],
        "ruleset": args.ruleset,
        "homepage": args.homepage,
        "source": source_rel,
    }

    svg_path: Path = args.output_svg
    json_path: Path = args.output_json
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    svg_path.write_text(svg, encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {svg_path} ({svg_path.stat().st_size} bytes)")
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
