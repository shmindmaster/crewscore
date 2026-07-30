#!/usr/bin/env python3
"""Build a reproducible competitive matrix from public sources + live CrewScore metadata.

No interviews. Network optional: offline mode fills CrewScore only and uses
cached AgentLinter facts if present.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "competitors"
JSON_PATH = OUT_DIR / "agentlinter-matrix.json"
MD_PATH = OUT_DIR / "agentlinter.md"

# Public facts (verified from public marketing/README as of generation; stars
# refreshed when network is available).
AGENTLINTER_BASE = {
    "name": "AgentLinter",
    "repo": "seojoonkim/agentlinter",
    "homepage": "https://agentlinter.com",
    "install": "npx agentlinter",
    "license": "MIT",
    "claims": [
        "Score, diagnose, and auto-fix agent workspace",
        "Local scanning",
        "GitHub Action",
        "Weighted scoring dimensions (public marketing)",
    ],
    "offline_scan": True,
    "has_fix": True,
    "has_github_action": True,
}


def package_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else "0.0.0"


def crewscore_side() -> dict:
    import sys

    sys.path.insert(0, str(ROOT))
    from crewscore import __version__
    from crewscore.scoring import DIMENSIONS, RULESET_ID
    from crewscore.scorers.structural_analysis import CONCEPT_COUNT

    return {
        "name": "CrewScore",
        "repo": "shmindmaster/crewscore",
        "homepage": "https://crewscore.ai",
        "install": "pip install crewscore",
        "package_version": __version__,
        "ruleset": RULESET_ID,
        "control_count": CONCEPT_COUNT,
        "dimensions": [key for _, key in DIMENSIONS],
        "dimension_weighting": "equal",
        "offline_scan": True,
        "has_fix": True,
        "has_github_action": True,
        "has_config_smells": True,
        "live_adversarial": False,
        "certification_claim": False,
        "score_meaning": "written-control coverage (checklist), not quality ranking",
    }


def fetch_github_stars(full_name: str) -> int | None:
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{full_name}",
            headers={"Accept": "application/vnd.github+json", "User-Agent": "crewscore-matrix"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return int(data.get("stargazers_count") or 0)
    except Exception:
        return None


def build(online: bool) -> dict:
    cs = crewscore_side()
    al = dict(AGENTLINTER_BASE)
    if online:
        al["stars"] = fetch_github_stars(al["repo"])
        cs["stars"] = fetch_github_stars(cs["repo"])
    else:
        al["stars"] = None
        cs["stars"] = None
    return {
        "generated": date.today().isoformat(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "online": online,
        "method": "public-docs-and-live-crewscore-metadata; no interviews",
        "crewscore": cs,
        "agentlinter": al,
        "differentiation": [
            "CrewScore separates system prompts (governance controls) from coding-agent config (smells).",
            "CrewScore publishes validation limits and known-poor dimensions explicitly.",
            "CrewScore score is equal-weight coverage of 23 controls unless corpus automation changes it.",
            "Neither product replaces runtime enforcement or live red-teaming.",
        ],
    }


def render_md(payload: dict) -> str:
    cs = payload["crewscore"]
    al = payload["agentlinter"]
    return f"""# Competitive matrix: CrewScore vs AgentLinter

Generated: `{payload["generated"]}` · method: {payload["method"]}

| | CrewScore | AgentLinter |
| --- | --- | --- |
| Install | `{cs["install"]}` | `{al["install"]}` |
| Repo | [{cs["repo"]}](https://github.com/{cs["repo"]}) | [{al["repo"]}](https://github.com/{al["repo"]}) |
| Stars (snapshot) | {cs.get("stars")} | {al.get("stars")} |
| Offline scan | {cs["offline_scan"]} | {al["offline_scan"]} |
| Fix / auto-fix | {cs["has_fix"]} | {al["has_fix"]} |
| GitHub Action | {cs["has_github_action"]} | {al["has_github_action"]} |
| Config smells path | {cs["has_config_smells"]} | (workspace lint framing) |
| Live adversarial | {cs["live_adversarial"]} | (not claimed here) |
| Certification claim | {cs["certification_claim"]} | (not claimed here) |
| CrewScore package | `{cs["package_version"]}` · `{cs["ruleset"]}` · {cs["control_count"]} controls | — |

## Differentiation

{chr(10).join(f"- {line}" for line in payload["differentiation"])}

## Honesty

This matrix is **public marketing + package metadata**, not a penetration test
of either tool. Stars and claims drift; regenerate with:

```bash
python scripts/generate_competitor_matrix.py --online
```
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--online",
        action="store_true",
        help="Fetch GitHub star counts (default: offline).",
    )
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = build(online=args.online)
    JSON_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_PATH.write_text(render_md(payload), encoding="utf-8")
    print(JSON_PATH)
    print(MD_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
