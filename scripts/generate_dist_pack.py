#!/usr/bin/env python3
"""Generate channel drafts from tracked launch-copy source and repository truth."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "launch-copy.json"
DEFAULT_OUTPUT_DIR = ROOT / "_production" / "launch" / "dist-pack"
REQUIRED_CHANNELS = ("show_hn", "x", "linkedin", "community_post")
ARTIFACTS = (
    "show-hn-title.txt",
    "show-hn-first-comment.md",
    "x-post.txt",
    "x-thread.md",
    "linkedin-post.md",
    "community-post.md",
    "answer-bank.md",
)
X_POST_LIMIT = 280
X_THREAD_MAX_TWEETS = 10
CHECKSUM_EXCLUDED_ARTIFACTS = {"checksums.txt"}
CHECKSUM_INCLUDE_ARTIFACTS = ARTIFACTS + ("manifest.json",)
CHECKSUM_EXPORT_ARTIFACTS = CHECKSUM_INCLUDE_ARTIFACTS + ("checksums.txt",)
SOURCE_MANIFEST_PATH = str(SOURCE.relative_to(ROOT)).replace("\\", "/")


def _version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else "0.0.0"


def _ruleset() -> str:
    import sys

    sys.path.insert(0, str(ROOT))
    from crewscore.scoring import RULESET_ID

    return RULESET_ID


def _dimension_count() -> int:
    import sys

    sys.path.insert(0, str(ROOT))
    from crewscore.scoring import DIMENSION_KEYS

    return len(DIMENSION_KEYS)


def _concept_count() -> int:
    import sys

    sys.path.insert(0, str(ROOT))
    from crewscore.scorers.structural_analysis import CONCEPT_COUNT

    return CONCEPT_COUNT


def _corpus_facts() -> dict[str, int | float]:
    path = ROOT / "docs" / "validation-corpus.json"
    if not path.exists():
        raise RuntimeError(f"validation corpus missing: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"validation corpus malformed JSON: {path}") from exc

    groups = raw.get("groups") or {}
    production = groups.get("production") or {}
    gpt_store = groups.get("gpt_store") or {}
    analysis = raw.get("analysis") or {}

    if not isinstance(groups, dict) or not isinstance(production, dict) or not isinstance(gpt_store, dict):
        raise RuntimeError(f"validation corpus missing required group structure: {path}")
    for field in ("files", "describe"):
        if field not in production or field not in gpt_store:
            raise RuntimeError(f"validation corpus missing required group fields in {path}")
    for entry in (production, gpt_store):
        if int(entry["files"]) <= 0:
            raise RuntimeError(f"validation corpus reports zero required evidence: {path}")
        if not isinstance(entry["describe"], dict) or "median" not in entry["describe"]:
            raise RuntimeError(f"validation corpus missing describe.median in {path}")
    if not isinstance(analysis, dict) or "delta" not in analysis or "p_value" not in analysis:
        raise RuntimeError(f"validation corpus missing required analysis fields in {path}")

    return {
        "total_prompts": int((production.get("files") or 0) + (gpt_store.get("files") or 0)),
        "production_n": int(production["files"]),
        "production_median": int((production["describe"] or {}).get("median")),
        "gpt_store_n": int(gpt_store["files"]),
        "gpt_store_median": int((gpt_store["describe"] or {}).get("median")),
        "cliffs_delta": float(analysis["delta"]),
        "p_value": float(analysis["p_value"]),
    }


def _readme_oneliner() -> str:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for line in readme.splitlines():
        if line.startswith("### "):
            return line.lstrip("# ").strip()
    return "Coverage-first structural checklist for AI agent prompts."


def _canonical_source_bytes() -> tuple[dict[str, Any], bytes]:
    if not SOURCE.exists():
        raise FileNotFoundError(f"launch-copy source not found: {SOURCE}")
    text = SOURCE.read_text(encoding="utf-8")
    source_bytes = text.replace("\r\n", "\n").encode("utf-8")
    payload = json.loads(source_bytes.decode("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("launch-copy source must be a JSON object")
    return payload, source_bytes


def _render_template(text: str, facts: dict[str, Any]) -> str:
    try:
        return text.format(**facts)
    except KeyError as exc:
        raise RuntimeError(f"launch-copy template key missing: {exc.args[0]}") from exc


def _next_sibling_path(path: Path, marker: str) -> Path:
    for index in range(1, 1000):
        candidate = path.parent / f"{path.name}.{marker}.{index}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not allocate exclusive sibling path for {path.name} ({marker})")


def _safe_remove(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)


def _copy_sibling_output(source: Path, sibling: Path) -> None:
    if source.exists():
        if not source.is_dir():
            raise RuntimeError(f"output path is not a directory: {source}")
        # Preserve unrelated links as links; never dereference content outside the pack.
        shutil.copytree(source, sibling, symlinks=True)
    else:
        sibling.mkdir(parents=True, exist_ok=True)


def _build_pack() -> tuple[dict[str, Any], bytes]:
    version = _version()
    corpus = _corpus_facts()
    source, source_bytes = _canonical_source_bytes()
    dimension_count = _dimension_count()
    channels = source.get("channels", {})

    for channel in REQUIRED_CHANNELS:
        if channel not in channels:
            raise RuntimeError(f"launch-copy source missing channel: {channel}")

    if not isinstance(channels.get("show_hn"), dict) or "title" not in channels["show_hn"] or "first_comment" not in channels["show_hn"]:
        raise RuntimeError("show_hn requires title and first_comment")

    for channel_name in ("x", "linkedin", "community_post"):
        if not isinstance(channels.get(channel_name), dict) or "text" not in channels[channel_name]:
            raise RuntimeError(f"{channel_name} requires text")

    x_channel = channels["x"]
    x_thread = x_channel.get("thread")
    if x_thread is not None:
        if not isinstance(x_thread, list) or not x_thread:
            raise RuntimeError("x.thread must be a non-empty list when present")
        if len(x_thread) > X_THREAD_MAX_TWEETS:
            raise RuntimeError(f"x.thread exceeds {X_THREAD_MAX_TWEETS} tweets")
        for index, tweet in enumerate(x_thread, start=1):
            if not isinstance(tweet, str) or not tweet.strip():
                raise RuntimeError(f"x.thread tweet {index} must be a non-empty string")

    answer_bank = source.get("answer_bank")
    if not isinstance(answer_bank, list) or not answer_bank:
        raise RuntimeError("launch-copy source requires a non-empty answer_bank")
    for item in answer_bank:
        if not isinstance(item, dict) or "question" not in item or "answer" not in item:
            raise RuntimeError("answer_bank items require question and answer")

    facts = {
        "package_version": version,
        "ruleset": _ruleset(),
        "dimension_count": _dimension_count(),
        "concept_count": _concept_count(),
        "production_n": corpus["production_n"],
        "production_median": corpus["production_median"],
        "gpt_store_n": corpus["gpt_store_n"],
        "gpt_store_median": corpus["gpt_store_median"],
        "total_prompts": corpus["total_prompts"],
        "cliffs_delta": corpus["cliffs_delta"],
        "p_value": corpus["p_value"],
        "validation_report_url": "https://github.com/shmindmaster/crewscore/blob/main/docs/validation-corpus.md",
        "validation_markdown": "https://github.com/shmindmaster/crewscore/blob/main/docs/validation.md",
        "created_by": "CrewScore is created and maintained by Sarosh Hussain.",
        "operating_context": "Pendoah is the company operating context for this project.",
        "oneliner": _readme_oneliner(),
    }

    x_rendered = {"text": _render_template(channels["x"]["text"], facts)}
    x_thread_texts = None
    if x_thread is not None:
        x_thread_texts = [_render_template(tweet, facts) for tweet in x_thread]
        for index, tweet in enumerate(x_thread_texts, start=1):
            if len(tweet) > X_POST_LIMIT:
                raise RuntimeError(f"x.thread tweet {index} exceeds {X_POST_LIMIT} characters: {len(tweet)}")
        x_rendered["thread"] = x_thread_texts

    rendered_channels = {
        "show_hn": {
            "title": _render_template(channels["show_hn"]["title"], facts),
            "first_comment": _render_template(channels["show_hn"]["first_comment"], facts),
        },
        "x": x_rendered,
        "linkedin": {"text": _render_template(channels["linkedin"]["text"], facts)},
        "community_post": {"text": _render_template(channels["community_post"]["text"], facts)},
    }

    return {
        "package_version": version,
        "ruleset": facts["ruleset"],
        "dimension_count": dimension_count,
        "channels": rendered_channels,
        "answer_bank": [
            {
                "question": _render_template(item["question"], facts),
                "answer": _render_template(item["answer"], facts),
            }
            for item in answer_bank
        ],
        "source": {
            "path": SOURCE_MANIFEST_PATH,
            "sha256": hashlib.sha256(source_bytes).hexdigest(),
        },
        "corpus": corpus,
        "posts_automatically": False,
        "anti_promise": source.get("anti_promise", ""),
        "note": "Drafts only. Post via optional APIs or paste; no interview process.",
    }, source_bytes


def _artifact_blobs(pack: dict[str, Any]) -> dict[str, str]:
    answer_bank = "\n\n".join(
        f"### {entry['question']}\n\n{entry['answer']}" for entry in pack["answer_bank"]
    )
    x_channel = pack["channels"]["x"]
    x_thread = x_channel.get("thread")
    x_thread_blob = "\n\n".join(x_thread) + "\n" if x_thread else ""
    return {
        "show-hn-title.txt": pack["channels"]["show_hn"]["title"],
        "show-hn-first-comment.md": pack["channels"]["show_hn"]["first_comment"],
        "x-post.txt": x_channel["text"],
        "x-thread.md": x_thread_blob,
        "linkedin-post.md": pack["channels"]["linkedin"]["text"],
        "community-post.md": pack["channels"]["community_post"]["text"],
        "answer-bank.md": answer_bank + "\n" if answer_bank else "",
    }


def _file_record(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "name": path.name,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }


def _prepare_generated_artifact(path: Path) -> None:
    """Remove a preserved link before writing a generated artifact into the pack."""
    if path.is_symlink():
        path.unlink()


def _write_artifacts(out: Path, artifacts: dict[str, str]) -> list[dict[str, Any]]:
    for name in ARTIFACTS:
        text = artifacts[name]
        payload = text + "\n" if not text.endswith("\n") else text
        path = out / name
        _prepare_generated_artifact(path)
        path.write_bytes(payload.replace("\r\n", "\n").encode("utf-8"))

    return [_file_record(out / name) for name in ARTIFACTS]


def _write_manifest(
    out: Path,
    pack: dict[str, Any],
    artifact_records: list[dict[str, Any]],
) -> dict[str, Any]:
    manifest = {
        "package_version": pack["package_version"],
        "ruleset": pack["ruleset"],
        "control_count": _concept_count(),
        "dimension_count": pack["dimension_count"],
        "source": pack["source"],
        "posts_automatically": pack["posts_automatically"],
        "corpus": pack["corpus"],
        "artifacts": artifact_records,
        "manifest_checksum_algorithm": "sha256",
        "checksum_includes": [row["name"] for row in artifact_records] + ["manifest.json"],
        "checksum_excludes": sorted(CHECKSUM_EXCLUDED_ARTIFACTS),
        "generated_by": "scripts/generate_dist_pack.py",
        "note": pack["note"],
    }
    manifest_path = out / "manifest.json"
    _prepare_generated_artifact(manifest_path)
    manifest_path.write_bytes((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    record = _file_record(manifest_path)
    return record


def _write_checksums(
    out: Path,
    records: list[dict[str, Any]],
    excluded_names: set[str],
) -> dict[str, Any]:
    included = sorted(
        (row for row in records if row["name"] not in excluded_names),
        key=lambda row: row["name"],
    )
    lines = [f"{row['sha256']}  {row['name']}" for row in included]
    path = out / "checksums.txt"
    _prepare_generated_artifact(path)
    path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    return _file_record(path)


def _validate_output_dir(path: Path) -> Path:
    for ancestor in [path] + list(path.parents):
        if ancestor.is_symlink():
            raise RuntimeError(f"refusing to write launch pack through symlink ancestor: {ancestor}")
    resolved = path.resolve()
    for forbidden in [ROOT, *ROOT.parents]:
        if resolved == forbidden:
            raise RuntimeError(f"refusing to write launch pack into workspace scope: {forbidden}")
    if path.exists() and not path.is_dir():
        raise RuntimeError(f"output directory is not a directory: {path}")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _build_pack_artifacts(pack: dict[str, Any], out: Path) -> list[dict[str, Any]]:
    artifacts = _artifact_blobs(pack)
    artifact_records = _write_artifacts(out, artifacts)
    manifest_record = _write_manifest(out, pack, artifact_records)
    checksums_record = _write_checksums(
        out,
        artifact_records + [manifest_record],
        CHECKSUM_EXCLUDED_ARTIFACTS | {"checksums.txt"},
    )
    return artifact_records + [manifest_record, checksums_record]


def _finalize_pack(
    pack: dict[str, Any],
    out: Path,
    *,
    fail_promotion: int = 0,
) -> list[dict[str, Any]]:
    candidate = _next_sibling_path(out, "candidate")
    backup: Path | None = None
    backup_created = False
    candidate_promoted = False
    try:
        _copy_sibling_output(out, candidate)
        records = _build_pack_artifacts(pack, candidate)

        checksums: dict[str, str] = {}
        for record in records:
            if record["name"] in CHECKSUM_EXCLUDED_ARTIFACTS:
                continue
            checksums[record["name"]] = record["sha256"]

        for name in CHECKSUM_INCLUDE_ARTIFACTS:
            if name not in checksums:
                raise RuntimeError(f"incomplete pack generation, missing artifact: {name}")

        if fail_promotion == 1:
            raise RuntimeError("injected failure before promotion")

        if out.exists():
            backup = _next_sibling_path(out, "backup")
            out.rename(backup)
            backup_created = True
            if fail_promotion == 2:
                raise RuntimeError("injected failure after backup")

        candidate.rename(out)
        candidate_promoted = True
        if fail_promotion == 3:
            raise RuntimeError("injected failure after promotion")

        if backup is not None and backup.exists():
            _safe_remove(backup)
        return records
    except Exception:
        if candidate_promoted and out.exists():
            _safe_remove(out)
        if backup_created:
            if backup is not None and backup.exists():
                backup.rename(out)
        raise
    finally:
        if candidate.exists():
            _safe_remove(candidate)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated drafts",
    )
    parser.add_argument(
        "--fail-promotion",
        type=int,
        default=0,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    out = _validate_output_dir(args.output_dir)

    pack, source_bytes = _build_pack()
    _ = source_bytes
    records = _finalize_pack(pack, out, fail_promotion=args.fail_promotion)
    manifest_record = next(record for record in records if record["name"] == "manifest.json")
    checksums_record = next(record for record in records if record["name"] == "checksums.txt")

    print(out)
    print(f"version={pack['package_version']}")
    print(f"checksum_file=sha256={checksums_record['sha256']} records={len(records) - 1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
