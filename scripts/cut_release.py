#!/usr/bin/env python3
"""Cut a release tag that matches the package version (agent-executable).

Does not publish itself — pushing the tag triggers .github/workflows/release.yml.

Usage:
  python scripts/cut_release.py           # dry-run: print intended tag
  python scripts/cut_release.py --push    # create annotated tag + push
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=check)


def package_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    if not match:
        raise SystemExit("version not found in pyproject.toml")
    return match.group(1)


def changelog_has_section(version: str) -> bool:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return f"## [{version}]" in text


def tag_exists(tag: str) -> bool:
    result = _run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"], check=False)
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--push",
        action="store_true",
        help="Create and push the annotated tag (otherwise dry-run only).",
    )
    args = parser.parse_args()

    version = package_version()
    tag = f"v{version}"
    if not changelog_has_section(version):
        print(f"ERROR: CHANGELOG.md missing section ## [{version}]", file=sys.stderr)
        return 1
    print(f"package_version={version}")
    print(f"intended_tag={tag}")
    print("changelog_section=ok")
    exists = tag_exists(tag)
    print(f"tag_exists={'1' if exists else '0'}")

    if not args.push:
        print("dry_run=1 (pass --push to create and push the tag)")
        return 0

    if exists:
        print(f"ERROR: tag {tag} already exists", file=sys.stderr)
        return 1

    msg = f"Release {tag}"
    _run(["git", "tag", "-a", tag, "-m", msg])
    _run(["git", "push", "origin", tag])
    print(f"pushed={tag}")
    print("release_workflow=triggered_by_tag_push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
