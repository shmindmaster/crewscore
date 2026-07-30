"""Agent-executable release and dist-pack generators stay honest."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cut_release_dry_run_matches_package_version():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "cut_release.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    out = result.stdout
    assert "package_version=" in out
    assert "intended_tag=v" in out
    assert "changelog_section=ok" in out
    assert "dry_run=1" in out


def test_generate_dist_pack_writes_anti_promise_drafts(tmp_path: Path):
    out = tmp_path / "pack"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "generate_dist_pack.py"),
            "--output-dir",
            str(out),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["posts_automatically"] is False
    blob = (out / "show-hn-first-comment.md").read_text(encoding="utf-8").lower()
    assert "not a red team" in blob or "not" in blob
    assert "agent-guard" not in blob
    assert "certification" in blob
    assert (out / "checksums.txt").is_file()
