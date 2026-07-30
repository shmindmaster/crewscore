#!/usr/bin/env python3
"""Collect automation-friendly product signals that replace interview PMF theater.

Outputs _production/signals/latest.json (gitignored working data). Network
optional; always includes package + corpus + ruleset facts from the repo.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_production" / "signals" / "latest.json"


def package_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else "0.0.0"


def ruleset_id() -> str:
    import sys

    sys.path.insert(0, str(ROOT))
    from crewscore.scoring import RULESET_ID

    return RULESET_ID


def corpus_snapshot() -> dict:
    path = ROOT / "docs" / "validation-corpus.json"
    if not path.is_file():
        return {"present": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    groups = data.get("groups") or {}
    return {
        "present": True,
        "groups": {
            name: {
                "files": g.get("files"),
                "median": (g.get("describe") or {}).get("median"),
            }
            for name, g in groups.items()
        },
    }


def github_repo_stats(full_name: str) -> dict:
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{full_name}",
            headers={"Accept": "application/vnd.github+json", "User-Agent": "crewscore-signals"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "stars": data.get("stargazers_count"),
            "forks": data.get("forks_count"),
            "open_issues": data.get("open_issues_count"),
            "watchers": data.get("subscribers_count"),
            "pushed_at": data.get("pushed_at"),
        }
    except Exception as exc:
        return {"error": str(exc)}


def pypi_downloads_hint(name: str) -> dict:
    """Best-effort public metadata (not a full download series)."""
    try:
        req = urllib.request.Request(
            f"https://pypi.org/pypi/{name}/json",
            headers={"User-Agent": "crewscore-signals"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        info = data.get("info") or {}
        return {
            "version": info.get("version"),
            "project_url": (info.get("project_urls") or {}).get("Homepage"),
            "requires_python": info.get("requires_python"),
        }
    except Exception as exc:
        return {"error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true")
    args = parser.parse_args()

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "method": "repo-facts + optional public APIs; replaces interview PMF backlog",
        "package_version": package_version(),
        "ruleset": ruleset_id(),
        "corpus": corpus_snapshot(),
        "automation_policy": {
            "merge": "required-ci-checks-and-owner-automerge",
            "pmf_interviews": "canceled",
            "gate0": "community-credibility-default",
            "category_vocab": "configuration-smells-and-written-controls",
        },
        "github": None,
        "pypi": None,
    }
    if args.online:
        payload["github"] = github_repo_stats("shmindmaster/crewscore")
        payload["pypi"] = pypi_downloads_hint("crewscore")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
