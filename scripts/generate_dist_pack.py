#!/usr/bin/env python3
"""Generate channel drafts from tracked launch-copy source and repository truth.

Writes under _production/launch/dist-pack/ by default (gitignored — channel
 drafts are working material, not published docs). Safe to regenerate; no
network posts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "launch" / "launch-copy.json"
DEFAULT_OUTPUT_DIR = ROOT / "_production" / "launch" / "dist-pack"
REQUIRED_CHANNELS = ("show_hn", "x", "linkedin", "community_post")
ARTIFACTS = (
    "show-hn-title.txt",
    "show-hn-first-comment.md",
    "x-post.txt",
    "linkedin-post.md",
    "community-post.md",
    "answer-bank.md",
)


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
    payload: dict[str, int | float] = {
        "total_prompts": 0,
        "production_n": 0,
        "production_median": 0,
        "gpt_store_n": 0,
        "gpt_store_median": 0,
        "cliffs_delta": 0.0,
        "p_value": 0.0,
    }
    if not path.exists():
        return payload
    raw = json.loads(path.read_text(encoding="utf-8"))
    groups = raw.get("groups") or {}
    production = groups.get("production") or {}
    gpt_store = groups.get("gpt_store") or {}
    analysis = raw.get("analysis") or {}
    return {
        "total_prompts": int((production.get("files") or 0) + (gpt_store.get("files") or 0)),
        "production_n": int(production.get("files") or 0),
        "production_median": int((production.get("describe") or {}).get("median") or 0),
        "gpt_store_n": int(gpt_store.get("files") or 0),
        "gpt_store_median": int((gpt_store.get("describe") or {}).get("median") or 0),
        "cliffs_delta": float(analysis.get("delta") or 0.0),
        "p_value": float(analysis.get("p_value") or 0.0),
    }


def _readme_oneliner() -> str:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for line in readme.splitlines():
        if line.startswith("### "):
            return line.lstrip("# ").strip()
    return "Coverage-first structural checklist for AI agent prompts."


def _load_source() -> dict[str, Any]:
    if not SOURCE.exists():
        raise FileNotFoundError(f"launch-copy source not found: {SOURCE}")
    payload: Any = json.loads(SOURCE.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("launch-copy source must be a JSON object")
    return payload


def _render_template(text: str, facts: dict[str, Any]) -> str:
    try:
        return text.format(**facts)
    except KeyError as exc:
        raise RuntimeError(f"launch-copy template key missing: {exc.args[0]}") from exc


def _build_pack() -> dict[str, Any]:
    version = _version()
    corpus = _corpus_facts()
    source = _load_source()
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

    rendered_channels = {
        "show_hn": {
            "title": _render_template(channels["show_hn"]["title"], facts),
            "first_comment": _render_template(channels["show_hn"]["first_comment"], facts),
        },
        "x": {"text": _render_template(channels["x"]["text"], facts)},
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
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        },
        "corpus": corpus,
        "posts_automatically": False,
        "anti_promise": source.get("anti_promise", ""),
        "note": "Drafts only. Post via optional APIs or paste; no interview process.",
    }


def _artifact_blobs(pack: dict[str, Any]) -> dict[str, str]:
    answer_bank = "\n\n".join(
        f"### {entry['question']}\n\n{entry['answer']}" for entry in pack["answer_bank"]
    )
    return {
        "show-hn-title.txt": pack["channels"]["show_hn"]["title"],
        "show-hn-first-comment.md": pack["channels"]["show_hn"]["first_comment"],
        "x-post.txt": pack["channels"]["x"]["text"],
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


def _write_artifacts(out: Path, artifacts: dict[str, str]) -> list[dict[str, Any]]:
    for name in ARTIFACTS:
        text = artifacts[name]
        (out / name).write_text(text + "\n" if not text.endswith("\n") else text, encoding="utf-8")

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
        "generated_by": "scripts/generate_dist_pack.py",
        "note": pack["note"],
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    record = _file_record(manifest_path)
    return record


def _write_checksums(out: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    lines = [f"{row['sha256']}  {row['name']}" for row in sorted(records, key=lambda row: row["name"])]
    path = out / "checksums.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return _file_record(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated drafts",
    )
    args = parser.parse_args()

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    for path in out.iterdir():
        if path.is_file():
            path.unlink()

    pack = _build_pack()
    artifacts = _artifact_blobs(pack)
    artifact_records = _write_artifacts(out, artifacts)
    manifest_record = _write_manifest(out, pack, artifact_records)
    checksums_record = _write_checksums(out, artifact_records + [manifest_record])
    checksums_record = _write_checksums(out, artifact_records + [manifest_record, checksums_record])

    print(out)
    print(f"version={pack['package_version']}")
    print(f"manifest=checksums={checksums_record['sha256']} records={len(artifact_records) + 2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
