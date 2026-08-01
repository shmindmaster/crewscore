"""Launch copy is a deterministic artifact derived from repository truth."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import shutil
from contextlib import contextmanager
from pathlib import Path
import pytest

from crewscore import __version__
from crewscore.scoring import DIMENSION_KEYS, RULESET_ID
from crewscore.scorers.structural_analysis import CONCEPT_COUNT

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "docs" / "launch-copy.json"
DATA = REPO / "docs" / "validation-corpus.json"
GENERATOR = REPO / "scripts" / "generate_dist_pack.py"
GIT_TRACKED_SOURCE = "docs/launch-copy.json"
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


def _launch_copy_source_bytes() -> bytes:
    text = SOURCE.read_text(encoding="utf-8")
    return text.replace("\r\n", "\n").encode("utf-8")
EXPECTED_CHECKSUM_NAMES = frozenset(
    {
        "show-hn-title.txt",
        "show-hn-first-comment.md",
        "x-post.txt",
        "linkedin-post.md",
        "community-post.md",
        "answer-bank.md",
        "manifest.json",
    }
)


def _generate_pack(path: Path) -> None:
    result = _generate_pack_raw(path)
    assert result.returncode == 0, result.stdout + result.stderr


def _generate_pack_raw(path: Path, *, extra_args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(GENERATOR), "--output-dir", str(path)]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(
        args,
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


@contextmanager
def _temporary_corpus(mutator) -> None:
    backup = DATA.with_suffix(".json.bak-launch-copy")
    if DATA.exists():
        shutil.copy2(DATA, backup)
    try:
        mutator()
        yield
    finally:
        if backup.exists():
            shutil.move(str(backup), DATA)


def _corpus_payload() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def _write_payload(payload: dict) -> None:
    DATA.write_text(json.dumps(payload), encoding="utf-8")


def _mutate_corpus_to_invalid_json() -> None:
    DATA.write_text("{", encoding="utf-8")


def _mutate_corpus_to_missing():
    DATA.write_text("{}", encoding="utf-8")


def _mutate_corpus_to_zero_evidence() -> None:
    payload = _corpus_payload()
    payload["groups"]["production"]["files"] = 0
    payload["groups"]["production"]["describe"]["median"] = 0
    _write_payload(payload)


def _mutate_corpus_to_unparseable():
    DATA.write_text("{\"groups\":", encoding="utf-8")


def _render_x_post() -> str:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    readme_line = next(
        (line.lstrip("# ").strip() for line in readme.splitlines() if line.startswith("### ")),
        "Coverage-first structural checklist for AI agent prompts.",
    )
    corpus = _corpus()
    facts = {
        "package_version": __version__,
        "ruleset": RULESET_ID,
        "dimension_count": len(DIMENSION_KEYS),
        "concept_count": CONCEPT_COUNT,
        "production_n": int(corpus["groups"]["production"]["files"]),
        "production_median": int(corpus["groups"]["production"]["describe"]["median"]),
        "gpt_store_n": int(corpus["groups"]["gpt_store"]["files"]),
        "gpt_store_median": int(corpus["groups"]["gpt_store"]["describe"]["median"]),
        "total_prompts": int(corpus["groups"]["production"]["files"] + corpus["groups"]["gpt_store"]["files"]),
        "cliffs_delta": float(corpus["analysis"]["delta"]),
        "p_value": float(corpus["analysis"]["p_value"]),
        "validation_report_url": "https://github.com/shmindmaster/crewscore/blob/main/docs/validation-corpus.md",
        "validation_markdown": "https://github.com/shmindmaster/crewscore/blob/main/docs/validation.md",
        "created_by": "CrewScore is created and maintained by Sarosh Hussain.",
        "operating_context": "Pendoah is the company operating context for this project.",
        "oneliner": readme_line,
    }
    x_text = source["channels"]["x"]["text"].format(**facts)
    return x_text if x_text.endswith("\n") else f"{x_text}\n"


def _snapshot_dir(path: Path) -> dict[str, str]:
    return {name: _sha256_file(path / name) for name in path.iterdir() if name.is_file()}


def test_generate_dist_pack_refuses_workspace_root_output():
    result = _generate_pack_raw(REPO)
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "refusing to write launch pack into workspace scope" in output


def test_generate_dist_pack_refuses_non_directory_output(tmp_path: Path):
    output = tmp_path / "file-output.txt"
    output.write_text("not-a-directory", encoding="utf-8")
    result = _generate_pack_raw(output)
    assert result.returncode != 0
    assert "output directory is not a directory" in (result.stdout + result.stderr)


def test_generate_dist_pack_preserves_unrelated_files(tmp_path: Path):
    out = tmp_path / "dist-pack"
    _generate_pack(out)

    unchanged = out / "sentinel.txt"
    unchanged.write_text("must remain", encoding="utf-8")
    sentinel_hash = _sha256_file(unchanged)
    artifacts = {name: _sha256_file(out / name) for name in REQUIRED_ARTIFACTS}
    _generate_pack(out)

    assert _sha256_file(unchanged) == sentinel_hash
    for name, expected_hash in artifacts.items():
        assert _sha256_file(out / name) == expected_hash


@pytest.mark.parametrize(
    "mutation",
    [
        _mutate_corpus_to_invalid_json,
        _mutate_corpus_to_missing,
        _mutate_corpus_to_zero_evidence,
        _mutate_corpus_to_unparseable,
    ],
)
def test_generate_dist_pack_fails_closed_on_bad_corpus(tmp_path: Path, mutation):
    out = tmp_path / "dist-pack"
    _generate_pack(out)
    baseline = _snapshot_dir(out)
    with _temporary_corpus(mutation):
        result = _generate_pack_raw(out)
    assert result.returncode != 0
    post = _snapshot_dir(out)
    assert post == baseline


def test_generate_dist_pack_x_channel_respects_post_limit(tmp_path: Path):
    x_text = _render_x_post()
    assert len(x_text) <= 280
    out = tmp_path / "dist-pack"
    _generate_pack(out)
    generated = (out / "x-post.txt").read_text(encoding="utf-8")
    assert generated == x_text
    assert len(generated) <= 280


def _corpus() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_checksums(lines: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for raw in lines.splitlines():
        if not raw.strip():
            continue
        assert "  " in raw, f"invalid checksum line {raw!r}"
        digest, name = raw.split("  ", 1)
        assert re.fullmatch(r"[0-9a-f]{64}", digest), f"invalid checksum {raw!r}"
        rows[name] = digest
    return rows


def _assert_no_unsupported_claims(text: str) -> None:
    lowered = text.lower()
    assert "quality score" not in lowered, "launch claim used unsupported quality-score framing"
    assert "safety score" not in lowered, "launch claim used unsupported safety-score framing"
    assert "certified" not in lowered, "launch claim used certification framing"
    assert "runtime proof" not in lowered, "launch claim used runtime-proof framing"

    assert "ship safer prompts" not in lowered, "launch claim used unsupported safety implication"
    assert "helps teams ship safer prompts" not in lowered, "launch claim used unsupported safety implication"
    if "runtime safety guarantee" in lowered:
        assert (
            "does not provide a runtime safety guarantee" in lowered
        ), "negate runtime safety-guarantee claim explicitly"


def _assert_checksums_match_artifacts(out: Path, checksums: dict[str, str]) -> None:
    assert set(checksums.keys()) == EXPECTED_CHECKSUM_NAMES
    assert "checksums.txt" not in checksums
    for name, digest in checksums.items():
        assert _sha256_file(out / name) == digest


def test_launch_copy_source_is_tracked():
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", GIT_TRACKED_SOURCE],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, f"{GIT_TRACKED_SOURCE} must be tracked"

    legacy_result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "docs/launch/launch-copy.json"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert legacy_result.returncode != 0, "legacy ignored launch source path must not be canonical tracked source"


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
    assert "smell scoring" not in source["channels"]["linkedin"]["text"]
    assert "configuration-smell findings" in source["channels"]["linkedin"]["text"]


def test_launch_copy_generated_pack_matches_repository_facts(tmp_path: Path):
    out = tmp_path / "dist-pack"
    _generate_pack(out)
    for name in REQUIRED_ARTIFACTS:
        assert (out / name).is_file(), f"missing artifact {name}"

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    source_bytes = _launch_copy_source_bytes()
    assert manifest["package_version"] == __version__
    assert manifest["ruleset"] == RULESET_ID
    assert manifest["control_count"] == CONCEPT_COUNT
    assert manifest["posts_automatically"] is False
    assert manifest["source"]["path"] == GIT_TRACKED_SOURCE
    assert manifest["source"]["sha256"] == hashlib.sha256(source_bytes).hexdigest()
    assert manifest["checksum_excludes"] == ["checksums.txt"]
    assert manifest["checksum_includes"] == [
        "show-hn-title.txt",
        "show-hn-first-comment.md",
        "x-post.txt",
        "linkedin-post.md",
        "community-post.md",
        "answer-bank.md",
        "manifest.json",
    ]

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
    checksums_by_name = _parse_checksums(checksums)
    _assert_checksums_match_artifacts(out, checksums_by_name)

    manifest_names = {artifact["name"] for artifact in manifest["artifacts"]}
    assert set(manifest_names) == {
        "show-hn-title.txt",
        "show-hn-first-comment.md",
        "x-post.txt",
        "linkedin-post.md",
        "community-post.md",
        "answer-bank.md",
    }


def test_launch_copy_generates_stable_checksums(tmp_path: Path):
    a = tmp_path / "dist-a"
    b = tmp_path / "dist-b"
    _generate_pack(a)
    _generate_pack(b)

    assert _corpus() is not None
    manifest_a = (a / "manifest.json").read_bytes()
    manifest_b = (b / "manifest.json").read_bytes()
    checksums_a = (a / "checksums.txt").read_bytes()
    checksums_b = (b / "checksums.txt").read_bytes()
    assert checksums_a == checksums_b
    assert manifest_a == manifest_b

    checksums_a_map = _parse_checksums(checksums_a.decode("utf-8"))
    checksums_b_map = _parse_checksums(checksums_b.decode("utf-8"))
    assert checksums_a_map == checksums_b_map
    assert set(checksums_a_map.keys()) == EXPECTED_CHECKSUM_NAMES
    for name in EXPECTED_CHECKSUM_NAMES:
        assert (a / name).read_bytes() == (b / name).read_bytes()
    for name in set(REQUIRED_ARTIFACTS):
        if name == "checksums.txt":
            continue
        assert _sha256_file(a / name) == checksums_a_map[name]


@pytest.mark.parametrize("fail_point", [1, 2, 3])
def test_generate_dist_pack_failures_rollback_candidate_to_preserve_prior_pack(tmp_path: Path, fail_point: int):
    out = tmp_path / "dist-pack"
    _generate_pack(out)

    sentinel = out / "sentinel.txt"
    sentinel.write_text("keep-me", encoding="utf-8")
    sentinel_before = _sha256_file(sentinel)
    before = _snapshot_dir(out)

    result = _generate_pack_raw(out, extra_args=[f"--fail-promotion={fail_point}"])
    assert result.returncode != 0

    assert before == _snapshot_dir(out)
    assert _sha256_file(sentinel) == sentinel_before
    assert not list(out.parent.glob(f"{out.name}.backup.*"))
    assert not list(out.parent.glob(f"{out.name}.candidate.*"))
