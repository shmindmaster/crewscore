#!/usr/bin/env python3
"""Export the Python structural scorer as score-engine.js for GitHub Pages."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from crewscore.web_export import build_payload, render_js  # noqa: E402


def main() -> int:
    out = ROOT / "score-engine.js"
    out.write_text(render_js(build_payload()), encoding="utf-8")
    print(f"Wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
