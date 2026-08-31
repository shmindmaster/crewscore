"""The per-file scores must reproduce the published aggregates.

This is the test that makes `docs/corpus-scores.json` worth publishing: it
proves the rows and the report are the same computation, so a reader can audit
every headline figure from the raw scores instead of trusting the summary.

It also pins the redistribution guarantee. The upstream collections are
licensed to their maintainers, not to us, so the emitted rows carry derived
data only — no path, no text, no matched span, no line number.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCORES = REPO / "docs" / "corpus-scores.json"
DATA = REPO / "docs" / "validation-corpus.json"

pytestmark = pytest.mark.skipif(
    not SCORES.exists() or not DATA.exists(),
    reason="run scripts/validate_corpus.py first",
)


@pytest.fixture(scope="module")
def scores() -> dict:
    return json.loads(SCORES.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def _by_corpus(scores: dict, key: str) -> list[dict]:
    return [r for r in scores["files"] if r["corpus"] == key]


def test_row_counts_match_the_report(scores, report):
    for key, group in report["groups"].items():
        assert len(_by_corpus(scores, key)) == group["files"]


def test_medians_and_zero_counts_reproduce(scores, report):
    """Recompute the distribution table from the rows."""
    for key, group in report["groups"].items():
        vals = [r["score"] for r in _by_corpus(scores, key)]
        d = group["describe"]
        assert statistics.median(vals) == pytest.approx(d["median"])
        assert max(vals) == d["max"]
        assert sum(1 for v in vals if v == 0) == d["zeros"]
        assert statistics.mean(vals) == pytest.approx(d["mean"], abs=0.01)


def test_per_control_hit_counts_reproduce(scores, report):
    """Every published per-control rate recomputes from controls_fired."""
    for row in report["controls"]:
        control = row["control"]
        for key in report["groups"]:
            fired = sum(
                1
                for r in _by_corpus(scores, key)
                if control in r["controls_fired"]
            )
            assert fired == row[f"{key}_hits"], f"{control} / {key}"


def test_never_fired_controls_are_absent_from_every_row(scores, report):
    absent = {r["control"] for r in report["never_fired"]}
    for r in scores["files"]:
        assert not absent & set(r["controls_fired"])


def test_rows_carry_derived_data_only(scores):
    """Schema whitelist. A path or an excerpt must never reach this file."""
    allowed = {"corpus", "file_id", "score", "bytes", "dimensions",
               "controls_fired"}
    for r in scores["files"]:
        assert set(r) == allowed, f"unexpected keys: {set(r) - allowed}"
        # A 16-hex id, not a path. Prompt filenames in the GPT-Store
        # collection are the assistants' own names and recur in the text.
        assert len(r["file_id"]) == 16
        int(r["file_id"], 16)


def test_file_ids_are_unique(scores):
    ids = [r["file_id"] for r in scores["files"]]
    assert len(ids) == len(set(ids))


def test_provenance_is_pinned(scores, report):
    """The rows must name the same commits the report was built from."""
    pinned = {c["key"]: c["sha"] for c in report["corpora"]}
    assert {k: v["sha"] for k, v in scores["generated_from"].items()} == pinned
    assert scores["ruleset"] == report["ruleset"]


def test_disclaimer_travels_with_the_data(scores):
    """It has to survive being loaded into someone else's notebook."""
    assert "not quality" in scores["disclaimer"]
    assert "not certification" in scores["disclaimer"]
