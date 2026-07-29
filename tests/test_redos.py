"""Every rule must stay linear in input length.

Ten rules were shaped `TRIGGER.*CLOSER`. When the trigger repeats and the
closer never appears, the engine retries the gap from every trigger position,
which is quadratic: 90 KB of one repeated trigger took ~10s through
`crewscore test --json`, and one rule took 31s at 160 KB in isolation.

The 500 KB input cap bounded that; it did not remove it. Bounding the gap
does, and is also more precise - these rules mean "trigger and closer near
each other", not "anywhere in the same line".

The budget is deliberately loose. It is sized to catch a return to quadratic
behaviour, not to police constant factors on a loaded CI box.
"""

from __future__ import annotations

import re
import time

import pytest

from crewscore.scorers.structural_analysis import SCORER_MAP, analyze

# Trigger for each rule that had an unbounded gap, chosen so the trigger
# matches and the closer never does - the shape that forces maximal
# backtracking.
ADVERSARIAL: dict[str, str] = {
    "injection.02": "do not follow to user ",
    "injection.03": "system prompt ",
    "injection.04": "reject ",
    "injection.09": "ignore ",
    "injection.08": "jailbreak ",
    "hallucination.01": "do not fabricate ",
    "hallucination.08": "recommend ",
    "human_gate.04": "do not auto ",
    "human_gate.05": "require ",
    "safe_stop.01": "stop ",
    "safe_stop.05": "escalate ",
}

_BUDGET_SECONDS = 2.0
_SIZE = 200_000


def _pattern_for(rule_id: str) -> str:
    dimension = rule_id.rsplit(".", 1)[0]
    for rid, pattern in SCORER_MAP[dimension]:
        if rid == rule_id:
            return pattern
    raise AssertionError(f"{rule_id} is not in the catalog")


def test_no_rule_contains_an_unbounded_gap():
    """The shape itself is the defect - ban it, don't just fix the instances."""
    offenders = [
        rule_id
        for patterns in SCORER_MAP.values()
        for rule_id, pattern in patterns
        if ".*" in pattern or ".+" in pattern
    ]
    assert not offenders, f"unbounded gap re-introduced in: {offenders}"


@pytest.mark.parametrize("rule_id", sorted(ADVERSARIAL))
def test_rule_is_linear_on_its_adversarial_input(rule_id):
    pattern = _pattern_for(rule_id)
    trigger = ADVERSARIAL[rule_id]
    text = trigger * (_SIZE // len(trigger))

    start = time.perf_counter()
    re.search(pattern, text, re.IGNORECASE)
    elapsed = time.perf_counter() - start

    assert elapsed < _BUDGET_SECONDS, (
        f"{rule_id} took {elapsed:.1f}s on {len(text)} chars "
        f"- the gap is unbounded again"
    )


def test_full_analysis_of_a_large_hostile_prompt_stays_fast():
    """The end-to-end path, not just one rule in isolation."""
    text = " ".join(ADVERSARIAL.values()) * 4_000
    assert len(text) > 400_000

    start = time.perf_counter()
    analyze(text)
    elapsed = time.perf_counter() - start

    assert elapsed < 10.0, f"analyze() took {elapsed:.1f}s on {len(text)} chars"
