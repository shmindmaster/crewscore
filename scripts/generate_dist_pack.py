#!/usr/bin/env python3
"""Generate channel drafts from repo truth (no interviews, no manual copy shop).

Writes under _production/launch/dist-pack/ by default (gitignored — channel
drafts are working material, not published docs). Safe to regenerate; no
network posts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else "0.0.0"


def _readme_oneliner() -> str:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for line in readme.splitlines():
        if line.startswith("### "):
            return line.lstrip("# ").strip()
    return "Offline written-control checklist for AI agent prompts."


def build_pack() -> dict:
    version = _version()
    one = _readme_oneliner()
    attribution = (
        "CrewScore is created and maintained by Sarosh Hussain. "
        "Pendoah is the company operating context for the project."
    )
    anti = (
        "CrewScore checks whether written guardrails are present in prompt text. "
        "It is not a red team, runtime enforcer, or safety certification."
    )
    show_hn_title = (
        f"Show HN: CrewScore – offline checklist for missing AI agent guardrails"
    )
    show_hn_comment = f"""\
CrewScore ({version}) is an offline, deterministic checker for AI agent system
prompts and coding-agent config (AGENTS.md smells).

What it is:
- 23 public written controls across 8 dimensions
- `crewscore scan .` + GitHub Action with control policies / SARIF
- Browser checker at https://crewscore.ai (prompt text is not uploaded; anonymous
  allowlisted usage events may be sent unless you opt out)

What it is not:
- {anti}

Install:
```
pip install crewscore
crewscore scan .
```

Repo: https://github.com/shmindmaster/crewscore
Validation: https://github.com/shmindmaster/crewscore/blob/main/docs/validation.md

{attribution}
"""
    x_post = (
        f"CrewScore {version}: find the written safety controls your agent prompt "
        f"forgot. Offline, no API key. {one} https://crewscore.ai"
    )
    linkedin = f"""\
{one}

CrewScore {version} scores whether published guardrails are written down —
injection defense, human approval, stop conditions, and more — for system
prompts and coding-agent config.

{anti}

Try: https://crewscore.ai
pip install crewscore

{attribution}
"""
    return {
        "generated": date.today().isoformat(),
        "package_version": version,
        "channels": {
            "show_hn": {"title": show_hn_title, "first_comment": show_hn_comment},
            "x": {"text": x_post},
            "linkedin": {"text": linkedin},
        },
        "anti_promise": anti,
        "attribution": attribution,
        "posts_automatically": False,
        "note": "Drafts only. Post via optional APIs or paste; no interview process.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "_production" / "launch" / "dist-pack",
        help="Directory for generated drafts",
    )
    args = parser.parse_args()
    out: Path = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    pack = build_pack()
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    (out / "show-hn-title.txt").write_text(pack["channels"]["show_hn"]["title"] + "\n", encoding="utf-8")
    (out / "show-hn-first-comment.md").write_text(
        pack["channels"]["show_hn"]["first_comment"], encoding="utf-8"
    )
    (out / "x-post.txt").write_text(pack["channels"]["x"]["text"] + "\n", encoding="utf-8")
    (out / "linkedin-post.md").write_text(pack["channels"]["linkedin"]["text"], encoding="utf-8")

    checksums = []
    for path in sorted(out.iterdir()):
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            checksums.append(f"{digest}  {path.name}")
    (out / "checksums.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")

    print(out)
    print(f"version={pack['package_version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
