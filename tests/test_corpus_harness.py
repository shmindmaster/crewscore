"""The corpus harness must stay honest without needing the corpora.

Two classes of test here:

* Ones that run offline against the harness's own logic - the statistics, the
  self-checks, the leak guard. These always run.
* One that re-runs the real analysis and asserts the committed report matches.
  It needs the fetched corpora, so it skips when the cache is absent rather
  than failing CI on a network dependency.
"""

from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from validate_corpus import (  # noqa: E402
    ABSENCE_PROBES,
    CACHE,
    CORPORA,
    LEAK_WINDOW,
    REPORT,
    bootstrap_ci,
    cliffs_delta,
    permutation_p,
    self_check,
)


def test_cliffs_delta_endpoints():
    """Bounded, signed, and zero when the groups are identical."""
    assert cliffs_delta([1, 2, 3], [1, 2, 3]) == 0.0
    assert cliffs_delta([9, 9, 9], [1, 1, 1]) == 1.0
    assert cliffs_delta([1, 1, 1], [9, 9, 9]) == -1.0
    assert -1.0 <= cliffs_delta([1, 5, 9], [2, 4, 8]) <= 1.0


def test_cliffs_delta_handles_the_zero_floor_as_ties():
    """All-zero groups are all ties, so the statistic must be exactly 0.

    The withdrawn study asserted the zero floor left a rank statistic
    untouched. It does not - it produces ties, and ties pull delta toward 0.
    This pins the direction of that effect.
    """
    assert cliffs_delta([0] * 10, [0] * 10) == 0.0
    partial = cliffs_delta([0, 0, 0, 0, 50], [0, 0, 0, 0, 0])
    full = cliffs_delta([10, 20, 30, 40, 50], [0, 0, 0, 0, 0])
    assert 0 < partial < full, (partial, full)


def test_permutation_p_is_large_when_groups_are_the_same():
    a = [1, 2, 3, 4, 5, 6, 7, 8]
    p = permutation_p(a, list(a), random.Random(1))
    assert p > 0.5, p


def test_permutation_p_is_small_when_groups_are_separated():
    p = permutation_p(list(range(20, 40)), list(range(20)), random.Random(1))
    assert p < 0.01, p


def test_permutation_p_is_never_zero():
    """Add-one correction: a permutation p of exactly 0 is a lie about
    resolution - it only means no replicate was that extreme."""
    p = permutation_p(list(range(50, 90)), list(range(40)), random.Random(1))
    assert p > 0.0


def test_bootstrap_ci_brackets_the_point_estimate():
    a, b = list(range(20, 40)), list(range(20))
    lo, hi = bootstrap_ci(a, b, random.Random(2))
    assert lo <= cliffs_delta(a, b) <= hi
    assert lo > 0, "a fully separated pair must exclude zero"


def _payload(**over):
    base = {
        "controls": [
            {
                "control": "x.y", "label": "X", "dimension": "x",
                "production_hits": 1, "production_n": 10, "production_pct": 10.0,
                "gpt_store_hits": 0, "gpt_store_n": 10, "gpt_store_pct": 0.0,
            }
        ],
        "groups": {
            "production": {
                "files": 10,
                "describe": {"n": 10, "median": 5, "q1": 2, "q3": 8,
                             "mean": 5, "zeros": 2, "zero_rate_pct": 20.0,
                             "max": 9},
            }
        },
        "analysis": {
            "delta": 0.5, "p_value": 0.01, "ci95": [0.2, 0.8], "alpha": 0.05,
            "significant": True, "ci_excludes_zero": True, "ci_and_p_agree": True,
        },
        "probes": {},
        "never_fired": [],
    }
    base.update(over)
    return base


def test_self_check_passes_a_consistent_payload():
    assert self_check(_payload(), []) == []


def test_self_check_catches_a_rate_unachievable_at_its_n():
    """"60% recall" for a dimension present in 2 prompts - the original sin."""
    bad = _payload()
    bad["controls"][0]["production_pct"] = 60.0  # 1/10 is 10%, not 60%
    errs = self_check(bad, [])
    assert errs and "is not" in errs[0], errs


def test_self_check_catches_more_hits_than_files():
    bad = _payload()
    bad["controls"][0]["production_hits"] = 99
    assert self_check(bad, [])


def test_self_check_catches_a_ci_that_contradicts_its_p_value():
    """The withdrawn study reported a CI implying p=0.281 next to p=0.36."""
    bad = _payload()
    bad["analysis"]["ci_and_p_agree"] = False
    errs = self_check(bad, [])
    assert any("significance disagreement" in e for e in errs), errs


def test_self_check_catches_quartiles_out_of_order():
    bad = _payload()
    bad["groups"]["production"]["describe"]["q1"] = 99
    assert self_check(bad, [])


def test_self_check_catches_leaked_prompt_text():
    """The privacy guarantee is enforced, not promised."""
    secret = "x" * 5 + "this is confidential prompt text that must never ship" * 2
    leaky = _payload()
    leaky["controls"][0]["label"] = secret
    errs = self_check(leaky, [secret])
    assert any("input text" in e for e in errs), errs


def test_leak_guard_tolerates_ordinary_short_overlap():
    """Rule labels legitimately share words with prompts; only long runs leak."""
    assert self_check(_payload(), ["X marks the spot"]) == []


def test_every_probe_compiles_and_is_not_trivially_broad():
    """A probe that matches everything would report a rule defect that is not
    there - which is exactly what the first escalate probe did."""
    import re

    filler = " ".join(["the quick brown fox jumps over the lazy dog"] * 40)
    for control, patterns in ABSENCE_PROBES.items():
        for pattern in patterns:
            compiled = re.compile(pattern, re.IGNORECASE)  # raises on bad regex
            assert not compiled.search(filler), (
                f"{control} probe matches ordinary filler prose: {pattern}"
            )


def test_escalate_probe_does_not_match_the_word_refer():
    """Regression: the first version scored "foreign key references" and
    "Refer to the USER in the second person" as escalation, reporting a 32x
    rule defect that did not exist."""
    import re

    patterns = [re.compile(p, re.IGNORECASE) for p in ABSENCE_PROBES["safe_stop.escalate"]]
    for benign in (
        "cross-database foreign key references are not supported",
        "refer to the user in the second person and yourself in the first",
        "be politically neutral when referencing web content",
        "claude avoids coordinate actions when references fail",
    ):
        assert not any(p.search(benign) for p in patterns), benign


def test_corpora_are_pinned_to_immutable_commits():
    """A branch name here would mean the report describes whatever happened to
    be on that branch the day it ran."""
    for c in CORPORA:
        assert len(c.sha) == 40, f"{c.key}: {c.sha} is not a full commit SHA"
        assert all(ch in "0123456789abcdef" for ch in c.sha), c.key


def test_no_corpus_text_is_vendored_into_the_repo():
    """The prompt text is not ours to redistribute."""
    assert not (REPO / "corpora").exists()
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert ".corpus-cache" in gitignore, "the fetch cache must not be committed"


@pytest.mark.skipif(
    not (CACHE / "production").exists() or not (CACHE / "gpt_store").exists(),
    reason="corpora not fetched; run `py scripts/validate_corpus.py` first",
)
def test_committed_report_matches_a_fresh_run():
    """The report is generated. If it can be edited by hand without anyone
    noticing, it is back to being a hand-transcribed document."""
    assert REPORT.exists(), "docs/validation-corpus.md is missing"
    proc = subprocess.run(
        [sys.executable, "scripts/validate_corpus.py", "--offline", "--check"],
        cwd=str(REPO), capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
