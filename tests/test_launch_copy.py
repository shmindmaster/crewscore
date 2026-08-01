"""Launch copy is a deterministic artifact derived from repository truth."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from crewscore import __version__
from crewscore.scoring import RULESET_ID
from crewscore.scorers.structural_analysis import CONCEPT_COUNT

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "docs" / "launch" / "launch-copy.json"
DATA = REPO / "docs" / "validation-corpus.json"
GENERATOR = REPO / "scripts" / "generate_dist_pack.py"
REQUIRED_ARTIFACTS = (
    "show-hn-title.txt",
    "show-hn-first-comment.md",
    "x-post.txt",
    "linkedin-post.md",
    "community-post.md",
    "answer-bank.md",
    "manifest.json",
    "checksums.txt",
)


def _generate_pack(path: Path) -> None:
    subprocess.run(
        [sys.executable, str(GENERATOR), "--output-dir", str(path)],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )


def _corpus() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def _assert_no_unsupported_claims(text: str) -> None:
    lowered = text.lower()
    assert "quality score" not in lowered, "launch claim used unsupported quality-score framing"
    assert "certified" not in lowered, "launch claim used certification framing"
    assert "not a certification" in lowered, "explicit anti-claim must remain present"
    assert "runtime proof" not in lowered, "launch claim used runtime-proof framing"
    assert "does not provide a runtime safety guarantee" in lowered, "explicit anti-claim must remain present for guarantee framing"
    assert "guarantee" not in lowered.replace("does not provide a runtime safety guarantee", ""), "launch claim used guarantee framing"
    assert "safety certification" not in lowered.replace("not a runtime safety certification", ""), "launch claim used safety certification"
    assert "safety score" not in lowered


def _artifact_names_in_checksums(lines: str) -> set[str]:
    names = set()
    for raw in lines.splitlines():
        if not raw.strip():
            continue
        _, name = raw.split("  ", 1)
        names.add(name)
    return names


def test_launch_copy_source_is_locked_and_template_driven():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    for key in ("show_hn", "x", "linkedin", "community_post"):
        assert key in source["channels"], f"missing channel {key}"

    assert isinstance(source.get("answer_bank"), list) and source["answer_bank"], "answer bank is empty"
    assert "anti_promise" in source
    assert "{package_version}" in source["channels"]["show_hn"]["first_comment"]
    assert "{package_version}" in source["channels"]["x"]["text"]
    assert "{package_version}" in source["channels"]["linkedin"]["text"]
    assert "{package_version}" in source["channels"]["community_post"]["text"]
    assert "{production_n}" in source["channels"]["show_hn"]["first_comment"]
    assert "{cliffs_delta}" in source["channels"]["show_hn"]["first_comment"]
    assert "{p_value}" in source["channels"]["show_hn"]["first_comment"]
    assert source["channels"]["show_hn"]["first_comment"].count("{dimension_count}") == 1


def test_launch_copy_generated_pack_matches_repository_facts(tmp_path: Path):
    out = tmp_path / "dist-pack"
    _generate_pack(out)
    for name in REQUIRED_ARTIFACTS:
        assert (out / name).is_file(), f"missing artifact {name}"

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["package_version"] == __version__
    assert manifest["ruleset"] == RULESET_ID
    assert manifest["control_count"] == CONCEPT_COUNT
    assert manifest["posts_automatically"] is False

    corpus = _corpus()
    assert manifest["corpus"]["production_n"] == corpus["groups"]["production"]["files"]
    assert manifest["corpus"]["production_median"] == corpus["groups"]["production"]["describe"]["median"]
    assert manifest["corpus"]["cliffs_delta"] == corpus["analysis"]["delta"]
    assert manifest["corpus"]["p_value"] == corpus["analysis"]["p_value"]

    artifacts_text = "\n".join(
        (out / name).read_text(encoding="utf-8").lower() for name in REQUIRED_ARTIFACTS
    )
    assert __version__ in artifacts_text
    total = str(corpus["groups"]["production"]["files"] + corpus["groups"]["gpt_store"]["files"])
    production_median = str(corpus["groups"]["production"]["describe"]["median"])
    assert total in artifacts_text
    assert f"{production_median}/100" in artifacts_text
    assert str(corpus["analysis"]["delta"]) in artifacts_text
    assert str(corpus["analysis"]["p_value"]) in artifacts_text
    _assert_no_unsupported_claims(artifacts_text)

    for stale in ("0.6.2", "0.6.3", "0.6.8"):
        assert stale not in artifacts_text, f"stale version surfaced: {stale}"

    checksums = (out / "checksums.txt").read_text(encoding="utf-8")
    manifest_names = _artifact_names_in_checksums(checksums)
    assert manifest_names == set(artifact["name"] for artifact in manifest["artifacts"]) | {"manifest.json", "checksums.txt"}


def test_launch_copy_generates_stable_checksums(tmp_path: Path):
    a = tmp_path / "dist-a"
    b = tmp_path / "dist-b"
    _generate_pack(a)
    _generate_pack(b)

    assert _corpus() is not None
    manifest_a = (a / "manifest.json").read_text(encoding="utf-8")
    manifest_b = (b / "manifest.json").read_text(encoding="utf-8")
    checksums_a = (a / "checksums.txt").read_text(encoding="utf-8")
    checksums_b = (b / "checksums.txt").read_text(encoding="utf-8")
    assert checksums_a == checksums_b
    assert manifest_a == manifest_b

    for line in checksums_a.splitlines():
        if not line.strip():
            continue
        digest = line.split("  ", 1)[0]
        assert re.fullmatch(r"[0-9a-f]{64}", digest), f"invalid digest line {line!r}"
