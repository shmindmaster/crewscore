"""Launch copy must quote the harness, not the author's memory.

`docs/launch-copy.md` carries drafts for X, LinkedIn, Facebook, HN and Reddit.
Every one leads with a measured figure, which makes it the highest-risk
document in the repo: a number that drifts here is wrong in public, on a
platform with no errata, in front of the audience most likely to check.

The withdrawn corpus study was exactly this failure at smaller scale - a real
analysis, re-typed into prose, wrong by the time anyone read it. So the figures
are read back out of the generated report.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
COPY = REPO / "docs" / "launch-copy.md"
DATA = REPO / "docs" / "validation-corpus.json"


def _copy() -> str:
    return COPY.read_text(encoding="utf-8")


def _drafts() -> str:
    """Only the text that actually ships.

    The file opens with a "what you may not claim" block that necessarily
    quotes the phrases it bans, so scanning the whole document for them finds
    the guardrail and calls it a violation.
    """
    text = _copy()
    start = text.find("## X / Twitter")
    assert start > 0, "launch copy has no drafts section"
    return text[start:]


def _data() -> dict:
    if not DATA.exists():
        pytest.skip("corpus report not generated")
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_corpus_size_is_the_measured_one():
    data = _data()
    total = sum(g["files"] for g in data["groups"].values())
    text = _copy()
    # Any "<number> ... prompts" phrase, however it is dressed up. An earlier
    # version enumerated the adjectives and missed "356 real AI agent *system*
    # prompts" - the exact phrasing used in three of the drafts.
    quoted = {
        int(n)
        for n in re.findall(r"\b(\d+)\s+(?:[a-zA-Z/-]+\s+){0,4}prompts\b", text)
    }
    per_group = {g["files"] for g in data["groups"].values()}
    stale = {n for n in quoted if n != total and n not in per_group}
    assert not stale, (
        f"launch copy quotes corpus sizes {sorted(stale)}; the harness "
        f"measured {total} ({sorted(per_group)} per group)"
    )
    assert str(total) in text, f"launch copy never states the corpus size {total}"


def test_production_median_is_the_measured_one():
    data = _data()
    median = data["groups"]["production"]["describe"]["median"]
    text = _copy()
    assert f"{median}/100" in text or f"{median} out of 100" in text, (
        f"launch copy does not carry the measured production median ({median})"
    )
    # The claim appears many times across platforms; none may disagree.
    other = {
        int(m) for m in re.findall(r"\bMedian(?:[^.\n]{0,30}?):?\s*(\d+)\s*(?:/100|out of 100)", text)
    }
    assert other <= {median}, (
        f"launch copy quotes medians {sorted(other)}; measured {median}"
    )


def test_production_median_is_scoped_to_the_production_subset():
    data = _data()
    production_n = data["groups"]["production"]["files"]
    median = data["groups"]["production"]["describe"]["median"]
    # Editorial objection prep quotes 14/100 but is not a launch draft.
    drafts = _drafts().split("**Comment prep", 1)[0].lower()
    for match in re.finditer(rf"\b{median}(?:/100| out of 100)\b", drafts):
        context = drafts[max(0, match.start() - 150) : match.end()]
        assert (
            f"{production_n} production" in context
            or "production median" in context
        ), f"unscoped production median: {context!r}"
    assert f"{sum(g['files'] for g in data['groups'].values())} production" not in drafts


def test_launch_copy_describes_browser_analytics_without_claiming_nothing_leaves():
    text = _drafts().lower()
    assert "nothing leaves your machine" not in text
    assert "entirely on your own machine" not in text
    assert "prompt text is never" in text or "prompt never" in text
    assert "anonymous allowlisted usage events may be sent unless you opt out" in text


def test_effect_size_and_p_value_are_the_measured_ones():
    data = _data()
    a = data["analysis"]
    text = _copy()
    assert str(a["delta"]) in text, f"delta {a['delta']} not in launch copy"
    assert str(a["p_value"]) in text, f"p {a['p_value']} not in launch copy"


def test_control_count_matches_the_catalog():
    from crewscore.scorers.structural_analysis import CONCEPT_COUNT

    text = _copy()
    quoted = {int(n) for n in re.findall(r"\b(\d+) (?:basic |distinct )?(?:safety )?controls\b", text)}
    stale = {n for n in quoted if n != CONCEPT_COUNT}
    assert not stale, (
        f"launch copy quotes control counts {sorted(stale)}; catalog has "
        f"{CONCEPT_COUNT}"
    )


def test_launch_copy_never_claims_quality_or_safety():
    """The one lie this launch could tell, banned in the file that would tell it.

    Every draft is written to say "coverage, not quality". A future edit that
    reaches for a punchier verb is the failure mode - "measures how good your
    prompt is" would be a bigger claim than the tool supports and would undo
    the reason anyone trusts it.
    """
    text = _drafts().lower()
    forbidden = [
        "measures prompt quality",
        "how good your prompt is",
        "makes your agent safe",
        "guarantees",
        "certifies",
        "proves your agent",
        "safety score",
        "security score",
    ]
    for phrase in forbidden:
        assert phrase not in text, f"launch copy overclaims: {phrase!r}"


def test_launch_copy_states_the_coverage_limit_explicitly():
    """Not overclaiming is not enough - the limit has to be said out loud, on
    the platforms where it will be quoted out of context."""
    text = _copy().lower()
    assert "coverage, not quality" in text
    assert "not a quality score" in text or "is not a quality score" in text


def test_launch_copy_carries_the_do_not_claim_list():
    """The guardrail for whoever edits this next, including a future me."""
    text = _copy()
    assert "What you may not claim" in text


def test_no_vendor_is_characterised_as_unsafe():
    """The corpus names real companies. The finding is that controls are rarely
    written down - not that anyone's product is dangerous. Saying otherwise is
    defamatory and, worse, unsupported by the measurement.
    """
    text = _copy().lower()
    for vendor in ("anthropic", "openai", "cursor", "perplexity"):
        for slur in ("unsafe", "dangerous", "insecure", "negligent", "reckless"):
            assert f"{vendor} is {slur}" not in text
            assert f"{vendor}'s agents are {slur}" not in text
    assert "isn't a dunk" in text or "is not a dunk" in text, (
        "the copy must say plainly that this is not an attack on the vendors"
    )
