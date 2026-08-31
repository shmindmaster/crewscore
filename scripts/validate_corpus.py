"""Corpus validation harness — every statistic we publish, emitted by code.

    py scripts/validate_corpus.py            # fetch, analyse, write the report
    py scripts/validate_corpus.py --offline  # reuse an existing cache

The previous corpus study was withdrawn because an audit of our own document
found arithmetic that was not merely wrong but impossible: a recall of 60% for
a dimension present in 2 prompts; "1 in 283 (2.1%)"; a line total below the
minimum its own distributions require; a confidence interval inconsistent with
its stated p-value, for a test that was never named.

Every one of those was a *hand-transcribed* number. So the rule this harness
enforces is: no statistic reaches the write-up except by being computed here
and written to the report by this script. `docs/validation-corpus.md` is
generated. Editing it by hand is the failure mode, and a test fails if the
committed report does not match a fresh run.

Design constraints, from SH-2402:

* Corpora are **fetched at pinned SHAs, never vendored.** The leaked prompt
  text is not ours to redistribute — the CC0 on those collections covers the
  maintainer's compilation, not the underlying vendor text.
* **The test is named** for every figure, and significance comes from one
  procedure so a CI and a p-value cannot be quoted from different machinery.
* **Denominators print next to every rate.**
* **Self-checks fail the run** on internally impossible output.
* **No prompt text leaves the machine** — enforced by a scan of the output
  against the inputs, not by care.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import statistics
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from crewscore.scorers.structural_analysis import (  # noqa: E402
    CONCEPTS,
    SCORER_MAP,
    _match_patterns,
    covered_concepts,
)
from crewscore.scoring import RULESET_ID, overall_score  # noqa: E402
from crewscore import __version__  # noqa: E402

CACHE = REPO / ".corpus-cache"
REPORT = REPO / "docs" / "validation-corpus.md"
DATA = REPO / "docs" / "validation-corpus.json"
# Per-file scores. Derived data we own outright; the prompt text behind it is
# not ours to redistribute and never leaves the pinned upstream. Same run,
# same leak scan.
SCORES = REPO / "docs" / "corpus-scores.json"
SCORES_CSV = REPO / "docs" / "corpus-scores.csv"

SEED = 20260729
RESAMPLES = 10_000
ALPHA = 0.05
# Longest run of input text allowed to appear in the output. Long enough that
# ordinary words and rule labels pass, short enough that a leaked sentence
# cannot.
LEAK_WINDOW = 40


@dataclass(frozen=True)
class Corpus:
    key: str
    label: str
    url: str
    sha: str
    globs: tuple[str, ...]
    exclude: tuple[str, ...]
    license_note: str


CORPORA = (
    Corpus(
        key="production",
        label="Production-labeled agent system prompts",
        url="https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools",
        sha="2054f580b1203da061e8e3df3c6449de2ad7c322",
        globs=("**/*.txt",),
        # .json files are tool schemas, not instruction text; README/LICENSE
        # are the collection's own docs.
        exclude=("README", "LICENSE"),
        license_note=(
            "Collection is CC0 by its maintainer; the underlying vendor prompt "
            "text is not. Fetched at a pinned SHA, never redistributed here."
        ),
    ),
    Corpus(
        key="gpt_store",
        label="General-purpose GPT-Store prompts",
        url="https://github.com/linexjlin/GPTs",
        sha="3adfb7b38423b64a995057483c1f9007ed5f4da5",
        globs=("prompts/**/*.md",),
        exclude=("README", "LICENSE"),
        license_note=(
            "Collection is MIT by its maintainer; the underlying author text "
            "is not. Fetched at a pinned SHA, never redistributed here."
        ),
    ),
)


# Deliberately loose probes for controls the shipped rules rarely or never
# match. These are a DIAGNOSTIC and never touch a score: they exist to
# separate the two explanations for a control that reads as absent.
#
#   probe also finds ~nothing  -> the control is genuinely absent here
#   probe finds it, rules did not -> the rules are too narrow (a defect)
#
# Without this, "0/356" is uninterpretable, and an uninterpretable zero in a
# validation report is how the previous study went wrong.
ABSENCE_PROBES: dict[str, tuple[str, ...]] = {
    "hallucination.grounding": (
        r"based\s+(?:only\s+)?on\s+the\s+(?:provided|given|supplied|retrieved|"
        r"attached|following)\s+(?:context|document|source|information|data)",
        r"using\s+only\s+the\s+(?:provided\s+)?(?:context|document|source|information)",
        r"(?:answer|respond|reply)\s+(?:only\s+)?(?:from|using|with)\s+the\s+"
        r"(?:context|knowledge\s*base|provided|documents?|sources?)",
        r"(?:do\s+not|don't|never)\s+use\s+(?:any\s+)?(?:outside|external|prior|"
        r"your\s+own)\s+knowledge",
        r"if\s+(?:the\s+)?(?:answer|information|it)\s+is\s+not\s+(?:in|found\s+in|"
        r"contained\s+in)\s+the\s+(?:context|document|source)",
    ),
    # The bare "<domain> advice" branch matched topic labels inside refusal
    # lists ("Providing investment or financial advice") rather than an
    # instruction to defer. Require the instruction.
    "hallucination.defer_to_expert": (
        r"(?:consult|speak\s+(?:to|with)|contact|refer\s+them\s+to|"
        r"suggest\s+(?:they|the\s+user)\s+(?:speak|consult|contact))"
        r"\s+(?:a|an|your|with\s+a)?\s*"
        r"(?:qualified\s+|licensed\s+|trusted\s+)?"
        r"(?:doctor|physician|lawyer|attorney|accountant|clinician|"
        r"professional|specialist|advisor)",
    ),
    # A first draft of this probe used a bare `refer` alternation with
    # `person|agent|team` as closers. It reported 32/356 against the rules'
    # 1/356 - which read as a 32x rule defect until the matches were
    # inspected: "foreign key references", "Refer to the USER in the second
    # person", "referencing web content". Every one was the ordinary English
    # word. A probe is only useful if its own false positives are bounded, so
    # the verbs now require the escalation sense and the closers exclude
    # "agent" (a software agent, in these corpora) and "person".
    "safe_stop.escalate": (
        r"(?:escalate|hand\s*(?:it\s*)?off|hand\s+over|transfer)"
        r"\s+(?:\w+\s+){0,4}?to\s+(?:a\s+|the\s+)?"
        r"(?:human|supervisor|operator|live\s+agent|support\s+team)",
        r"(?:connect|forward)\s+(?:the\s+)?(?:user|customer)\s+to\s+a\s+human",
    ),
    "audit.tamper_evident": (
        r"immutab|append.only|tamper|write.once|read.only\s+log",
    ),
    # 0.6.0 diagnostics: separate "rules too narrow" from "absent" for the
    # three historically weak dimensions without scoring on these probes.
    "cost.budget_cap": (
        r"(?:token|cost|spend|inference)\s*(?:budget|limit|cap|ceiling)",
        r"budget\s*(?:for\s+)?(?:token|cost|spend|inference)",
        r"max_tokens|max_output_tokens",
    ),
    "cost.output_bound": (
        r"(?:max|maximum)\s*(?:response|output|completion|token)",
        r"(?:response|output)\s*(?:length|limit|cap)",
        r"truncat(?:e|ion)\s+(?:response|output|answer)",
    ),
    "audit.log_actions": (
        r"\b(?:log|record|track)\b.{0,40}?\b(?:action|decision|tool|call)\b",
        r"\baudit\s+trail\b",
        r"\bdecision\s+log\b",
    ),
    "audit.actor_attribution": (
        r"who\s+did\s+what",
        r"(?:record|log)\s+who",
        r"approver\s+and\s+time",
        r"actor\s+attribution",
    ),
    "compliance.named_regime": (
        r"\bhipaa\b|\bgdpr\b|\bsoc\s*2\b|\beu\s+ai\s+act\b|\bferpa\b|"
        r"\bpci[\s-]?dss\b|\bphi\b",
    ),
    "compliance.data_protection": (
        r"(?:encrypt|redact|de[\s-]?identif|anonymi).{0,40}?"
        r"(?:personal|pii|phi|sensitive|user\s+data)",
        r"(?:personal|pii|phi|sensitive).{0,40}?"
        r"(?:encrypt|redact|de[\s-]?identif|anonymi)",
    ),
    "human_gate.approval_required": (
        r"(?:ask|request|obtain|get|seek)\s+(?:for\s+)?(?:the\s+)?"
        r"(?:user|human|explicit)?\s*(?:permission|approval|consent|confirmation)",
        r"confirm\s+(?:with\s+)?(?:the\s+)?(?:user|human)\s+before",
    ),
    "injection.prompt_confidentiality": (
        r"(?:do\s+not|don't|never)\s+(?:reveal|share|disclose|expose|output|"
        r"repeat|print)\s+(?:the\s+|your\s+|this\s+)?"
        r"(?:system\s+prompt|instructions|prompt|these\s+rules)",
        r"(?:confidential|secret|private)\s+.{0,30}?(?:instructions|prompt)",
    ),
}


# ─── fetch ────────────────────────────────────────────────────────────

def fetch(corpus: Corpus, *, offline: bool) -> Path:
    dest = CACHE / corpus.key
    if dest.exists():
        have = _git(dest, "rev-parse", "HEAD")
        if have == corpus.sha:
            return dest
        if offline:
            raise SystemExit(
                f"{corpus.key}: cache is at {have[:8]}, manifest pins "
                f"{corpus.sha[:8]}; re-run without --offline"
            )
    if offline:
        raise SystemExit(f"{corpus.key}: no cache at {dest} and --offline given")

    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        subprocess.run(
            ["git", "init", "-q", str(dest)], check=True, cwd=str(dest.parent)
        )
        _git(dest, "remote", "add", "origin", corpus.url)
    # Fetch exactly the pinned commit: a moving default branch cannot change
    # what this harness measured.
    _git(dest, "fetch", "-q", "--depth", "1", "origin", corpus.sha)
    _git(dest, "checkout", "-q", "--detach", "FETCH_HEAD")
    got = _git(dest, "rev-parse", "HEAD")
    if got != corpus.sha:
        raise SystemExit(f"{corpus.key}: fetched {got}, expected {corpus.sha}")
    return dest


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True
    ).stdout.strip()


def collect(corpus: Corpus, root: Path) -> list[tuple[str, str]]:
    """Return (relative_path, text). Paths are public; text never leaves."""
    seen: dict[str, str] = {}
    for pattern in corpus.globs:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            if any(x.lower() in path.stem.lower() for x in corpus.exclude):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if len(text.split()) < 20:  # stub or index file, not a prompt
                continue
            seen[str(path.relative_to(root)).replace("\\", "/")] = text
    return sorted(seen.items())


# ─── statistics ───────────────────────────────────────────────────────
#
# One statistic (Cliff's delta), one significance procedure (a permutation
# test on that same statistic), one interval (a bootstrap of that same
# statistic). Naming them here rather than in prose is the point: the
# withdrawn study quoted a CI and a p-value that could not both be true, for
# a test it never named.


def _midranks(values: list[float]) -> list[float]:
    """Ranks with ties averaged. Ties matter here — see the zero-floor note."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def cliffs_delta(a: list[float], b: list[float]) -> float:
    """P(a>b) - P(a<b), via the Mann-Whitney U identity.

    delta = 2U/(n1*n2) - 1, where U comes from midranks — so ties (of which
    the zero floor produces many) are handled explicitly rather than ignored.
    """
    n1, n2 = len(a), len(b)
    if not n1 or not n2:
        return 0.0
    ranks = _midranks(a + b)
    r1 = sum(ranks[:n1])
    u1 = r1 - n1 * (n1 + 1) / 2.0
    return 2.0 * u1 / (n1 * n2) - 1.0


def permutation_p(a: list[float], b: list[float], rng: random.Random) -> float:
    """Two-sided permutation test on Cliff's delta.

    The pooled ranks are fixed under label permutation, so each replicate is a
    resample of ranks rather than a re-sort — exact, and fast enough to run
    the full 10,000 without approximating.
    """
    n1, n2 = len(a), len(b)
    observed = abs(cliffs_delta(a, b))
    pooled_ranks = _midranks(a + b)
    denom = n1 * n2
    offset = n1 * (n1 + 1) / 2.0
    extreme = 0
    for _ in range(RESAMPLES):
        rng.shuffle(pooled_ranks)
        u1 = sum(pooled_ranks[:n1]) - offset
        if abs(2.0 * u1 / denom - 1.0) >= observed - 1e-12:
            extreme += 1
    # Add-one correction: a permutation p is never exactly 0.
    return (extreme + 1) / (RESAMPLES + 1)


def bootstrap_ci(
    a: list[float], b: list[float], rng: random.Random
) -> tuple[float, float]:
    """Percentile bootstrap CI for Cliff's delta, resampling within groups."""
    deltas = []
    for _ in range(RESAMPLES):
        ra = [a[rng.randrange(len(a))] for _ in range(len(a))]
        rb = [b[rng.randrange(len(b))] for _ in range(len(b))]
        deltas.append(cliffs_delta(ra, rb))
    deltas.sort()
    lo = deltas[int((ALPHA / 2) * len(deltas))]
    hi = deltas[min(len(deltas) - 1, int((1 - ALPHA / 2) * len(deltas)))]
    return lo, hi


def describe(values: list[float]) -> dict:
    s = sorted(values)
    n = len(s)
    return {
        "n": n,
        "median": statistics.median(s) if n else 0,
        "q1": s[n // 4] if n else 0,
        "q3": s[(3 * n) // 4] if n else 0,
        "mean": round(statistics.fmean(s), 2) if n else 0,
        "zeros": sum(1 for v in s if v == 0),
        "zero_rate_pct": round(100 * sum(1 for v in s if v == 0) / n, 1) if n else 0,
        "max": s[-1] if n else 0,
    }


# ─── analysis ─────────────────────────────────────────────────────────


def score_corpus(files: list[tuple[str, str]]) -> dict:
    overalls: list[float] = []
    control_hits: dict[str, int] = {
        c.key: 0 for cs in CONCEPTS.values() for c in cs
    }
    # Per-file rows. The aggregate numbers below are computed from exactly
    # these records, so publishing them lets a reader audit every headline
    # figure from the raw scores. Derived data only: no prompt text, no
    # matched spans, no line numbers. See docs/corpus-scores.md.
    per_file: list[dict] = []
    for path, text in files:
        lowered = text.lower()
        dims = {}
        fired: list[str] = []
        for dimension, patterns in SCORER_MAP.items():
            matched = {rid for rid, _, _ in _match_patterns(lowered, patterns)}
            covered = covered_concepts(dimension, matched)
            for c in covered:
                control_hits[c.key] += 1
                fired.append(c.key)
            total = len(CONCEPTS[dimension])
            k = len(covered)
            dims[dimension] = 0 if not k else (100 * k + total // 2) // total
        score = overall_score(dims)
        overalls.append(score)
        # Opaque, deterministic id instead of the path.
        #
        # Not caution — a measurement. The leak scan rejected paths on
        # 2026-08-24 with the window 'T Customizer, File Finder & JSON Action'.
        # In the GPT-Store collection the filename *is* the assistant's name
        # and the prompt text restates it, so a path is prompt content wearing
        # a different hat. Publishing it would redistribute exactly what the
        # licence notes say is not ours to redistribute.
        #
        # The id is sha256 of the upstream-relative path, so anyone can
        # regenerate the mapping locally from the pinned SHA and audit any row.
        # Nothing is hidden; it just is not restated here.
        per_file.append(
            {
                "file_id": hashlib.sha256(path.encode("utf-8")).hexdigest()[:16],
                "score": score,
                "bytes": len(text),
                "dimensions": dict(dims),
                "controls_fired": sorted(fired),
            }
        )
    return {
        "overalls": overalls,
        "control_hits": control_hits,
        "per_file": per_file,
    }


def analyse(groups: dict[str, dict], rng: random.Random) -> dict:
    prod = groups["production"]["overalls"]
    store = groups["gpt_store"]["overalls"]

    delta = cliffs_delta(prod, store)
    p = permutation_p(prod, store, random.Random(SEED))
    lo, hi = bootstrap_ci(prod, store, random.Random(SEED + 1))

    # The confound the withdrawn study asserted away: a large mass of exact
    # zeros creates ties, and ties attenuate a rank statistic rather than
    # leaving it untouched. Report the tie mass, then re-run without it.
    nz_prod = [v for v in prod if v > 0]
    nz_store = [v for v in store if v > 0]
    sens = None
    if len(nz_prod) >= 5 and len(nz_store) >= 5:
        sens = {
            "n_production": len(nz_prod),
            "n_gpt_store": len(nz_store),
            "delta": round(cliffs_delta(nz_prod, nz_store), 3),
            "p": round(permutation_p(nz_prod, nz_store, random.Random(SEED + 2)), 4),
        }

    ci_excludes_zero = (lo > 0 and hi > 0) or (lo < 0 and hi < 0)
    significant = p < ALPHA
    return {
        "statistic": "Cliff's delta (Mann-Whitney U identity, midranks for ties)",
        "significance_test": (
            f"two-sided permutation test on Cliff's delta, {RESAMPLES} "
            f"relabelings, seed {SEED}, add-one corrected"
        ),
        "interval_method": (
            f"percentile bootstrap on the same statistic, {RESAMPLES} "
            f"resamples within groups, seed {SEED + 1}"
        ),
        "delta": round(delta, 3),
        "p_value": round(p, 4),
        "ci95": [round(lo, 3), round(hi, 3)],
        "alpha": ALPHA,
        "significant": significant,
        "ci_excludes_zero": ci_excludes_zero,
        "ci_and_p_agree": significant == ci_excludes_zero,
        "zero_floor_sensitivity": sens,
    }


def control_table(groups: dict[str, dict]) -> list[dict]:
    rows = []
    labels = {c.key: c.label for cs in CONCEPTS.values() for c in cs}
    for dimension, concepts in CONCEPTS.items():
        for c in concepts:
            row = {"control": c.key, "label": labels[c.key], "dimension": dimension}
            for key, g in groups.items():
                n = len(g["overalls"])
                hits = g["control_hits"][c.key]
                row[f"{key}_hits"] = hits
                row[f"{key}_n"] = n
                row[f"{key}_pct"] = round(100 * hits / n, 1) if n else 0.0
            rows.append(row)
    return rows


# ─── self-checks: these fail the run ──────────────────────────────────


def self_check(payload: dict, texts: list[str], extra: dict | None = None) -> list[str]:
    """Every failure mode from the withdrawn study, as an assertion."""
    errs: list[str] = []

    # 1. Every rate must be achievable at its own n. "60% recall" for a
    #    dimension present in 2 prompts is the error this catches.
    for row in payload["controls"]:
        for key in ("production", "gpt_store"):
            n, hits, pct = row[f"{key}_n"], row[f"{key}_hits"], row[f"{key}_pct"]
            if n == 0:
                continue
            if not 0 <= hits <= n:
                errs.append(f"{row['control']}/{key}: {hits} hits of {n}")
            if abs(pct - 100 * hits / n) > 0.05:
                errs.append(
                    f"{row['control']}/{key}: {pct}% is not {hits}/{n}"
                )

    # 2. Denominators must be present next to every rate.
    for row in payload["controls"]:
        for key in ("production", "gpt_store"):
            if f"{key}_n" not in row:
                errs.append(f"{row['control']}: rate without a denominator")

    # 3. The interval and the p-value must not contradict each other. They come
    #    from resampling the same statistic, so disagreement means a bug here,
    #    not a subtle result.
    a = payload["analysis"]
    if not a["ci_and_p_agree"]:
        errs.append(
            f"significance disagreement: p={a['p_value']} (alpha={a['alpha']}) "
            f"but CI95={a['ci95']}"
        )

    # 4. Cliff's delta is bounded.
    if not -1.0 <= a["delta"] <= 1.0:
        errs.append(f"delta {a['delta']} out of range")
    if not 0.0 < a["p_value"] <= 1.0:
        errs.append(f"p {a['p_value']} out of range")

    # 5. Group summaries must be internally consistent.
    for key, g in payload["groups"].items():
        d = g["describe"]
        if d["n"] != g["files"]:
            errs.append(f"{key}: n={d['n']} but {g['files']} files scored")
        if not 0 <= d["zeros"] <= d["n"]:
            errs.append(f"{key}: {d['zeros']} zeros of {d['n']}")
        if d["n"] and abs(d["zero_rate_pct"] - 100 * d["zeros"] / d["n"]) > 0.05:
            errs.append(f"{key}: zero rate does not match its own counts")
        if not d["q1"] <= d["median"] <= d["q3"]:
            errs.append(f"{key}: quartiles out of order")

    # 6. No prompt text may leave the machine. Checked against the inputs
    #    rather than trusted to discipline. `extra` carries any additional
    #    artifact written in the same run (the per-file scores), so a new
    #    output cannot quietly escape this scan.
    blob = json.dumps(payload) + ("" if extra is None else json.dumps(extra))
    for text in texts:
        squeezed = " ".join(text.split())
        for i in range(0, max(0, len(squeezed) - LEAK_WINDOW), LEAK_WINDOW):
            window = squeezed[i : i + LEAK_WINDOW]
            if window and window in blob:
                errs.append(
                    f"output contains {LEAK_WINDOW}+ chars of input text: "
                    f"{window!r}"
                )
                return errs
    return errs


def probe_absence(texts: list[str]) -> dict[str, dict]:
    """Run the loose diagnostic probes. Never affects a score."""
    lowered = [" ".join(t.lower().split()) for t in texts]
    out: dict[str, dict] = {}
    for control, patterns in ABSENCE_PROBES.items():
        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
        hits = sum(1 for t in lowered if any(c.search(t) for c in compiled))
        out[control] = {
            "hits": hits,
            "n": len(lowered),
            "pct": round(100 * hits / len(lowered), 1) if lowered else 0.0,
            "patterns": len(patterns),
        }
    return out


# ─── report ───────────────────────────────────────────────────────────


def render(payload: dict) -> str:
    a = payload["analysis"]
    g = payload["groups"]
    lines = [
        "<!-- GENERATED by scripts/validate_corpus.py - do not edit by hand.",
        "     Every number here is emitted by that script. Hand-transcription",
        "     is what produced the errors that got the previous study",
        "     withdrawn, so the report is generated and a test fails if this",
        "     file does not match a fresh run. -->",
        "",
        "# Corpus validation: does CrewScore coverage separate production-labeled "
        "prompts from general-purpose ones?",
        "",
        f"Validation ruleset `{payload['ruleset']}` · package `{__version__}` · generated from the committed corpus snapshot.",
        "Reproducible command: `py scripts/validate_corpus.py`. This supersedes the withdrawn 1,368-prompt study.",
        "",
        "## Corpora",
        "",
        "Fetched at pinned commits, never vendored into this repository.",
        "",
        "| Corpus | Files scored | Source | Pinned commit |",
        "| --- | ---: | --- | --- |",
    ]
    for c in CORPORA:
        lines.append(
            f"| {c.label} | {g[c.key]['files']} | [{c.url.split('github.com/')[-1]}]"
            f"({c.url}) | `{c.sha[:12]}` |"
        )
    lines += ["", "Licensing:", ""]
    for c in CORPORA:
        lines.append(f"- **{c.label}** — {c.license_note}")

    lines += [
        "",
        "## Score distribution",
        "",
        "| Corpus | n | Median | IQR | Mean | Scored 0 | Max |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for c in CORPORA:
        d = g[c.key]["describe"]
        lines.append(
            f"| {c.label} | {d['n']} | {d['median']} | {d['q1']}–{d['q3']} | "
            f"{d['mean']} | {d['zeros']}/{d['n']} ({d['zero_rate_pct']}%) | "
            f"{d['max']} |"
        )

    verdict = "separates" if a["significant"] else "does not separate"
    lines += [
        "",
        "## Discrimination",
        "",
        f"- **Statistic:** {a['statistic']}",
        f"- **Significance:** {a['significance_test']}",
        f"- **Interval:** {a['interval_method']}",
        "",
        f"**Cliff's delta = {a['delta']}**, 95% CI "
        f"[{a['ci95'][0]}, {a['ci95'][1]}], *p* = {a['p_value']}.",
        "",
        f"At alpha = {a['alpha']}, coverage **{verdict}** the two corpora.",
        "",
    ]
    if a["zero_floor_sensitivity"]:
        s = a["zero_floor_sensitivity"]
        lines += [
            "### The zero-floor confound, addressed rather than asserted away",
            "",
            "A mass of exact zeros creates ties, and ties **attenuate** a rank",
            "statistic rather than leaving it untouched. The withdrawn study",
            "claimed the opposite. Re-running on non-zero scores only:",
            "",
            f"- n = {s['n_production']} production, {s['n_gpt_store']} "
            "GPT-Store (scores above 0 only)",
            f"- Cliff's delta = {s['delta']}, *p* = {s['p']}",
            "",
            "Report both. If they point the same way the zero mass is not",
            "driving the result; if they diverge, that divergence is the",
            "finding.",
            "",
        ]

    lines += [
        "## Per-control coverage",
        "",
        "Every rate carries its denominator. A percentage without one is how",
        "\"1 prompt in 283 (2.1%)\" survived review.",
        "",
        "| Control | Production | GPT-Store |",
        "| --- | ---: | ---: |",
    ]
    for row in payload["controls"]:
        lines.append(
            f"| {row['label']} | {row['production_hits']}/{row['production_n']} "
            f"({row['production_pct']}%) | {row['gpt_store_hits']}/"
            f"{row['gpt_store_n']} ({row['gpt_store_pct']}%) |"
        )

    dead = payload["never_fired"]
    lines += ["", "## Controls that never fired", ""]
    if not dead:
        lines.append("Every control fired on at least one file in at least one corpus.")
    else:
        total = sum(gr["files"] for gr in g.values())
        lines += [
            f"**{len(dead)} of {len(payload['controls'])} controls matched nothing "
            f"in {total} publicly collected prompts.**",
            "",
        ]
        for row in dead:
            lines.append(f"- `{row['control']}` — {row['label']}")
        lines += [
            "",
            "A control that never fires contributes a guaranteed zero to every",
            "score, which caps the reachable maximum for reasons no reader can",
            "see. Two explanations need opposite fixes:",
            "",
            "1. **The control is genuinely absent** from prompts in the wild —",
            "   the zero is the finding, and the instrument is working.",
            "2. **The rules are too narrow to detect it** — the control is",
            "   stated in wording no pattern covers. That is a rule defect,",
            "   and from the outside it looks identical to (1).",
            "",
            "So the harness re-scans with deliberately looser probes than the",
            "shipped rules. The probes never touch a score; they exist only to",
            "tell these two cases apart. If a probe finds the control where the",
            "rules did not, the rules are the problem.",
            "",
            "| Control | Shipped rules | Loose probe | Reading |",
            "| --- | ---: | ---: | --- |",
        ]
        for row in dead:
            pr = payload["probes"].get(row["control"])
            if not pr:
                lines.append(
                    f"| {row['label']} | 0 | *no probe defined* | **unmeasured** "
                    "— write a probe before trusting this zero |"
                )
                continue
            # A probe finding materially more than the rules is a rule defect.
            defect = pr["hits"] >= max(3, 0.02 * pr["n"])
            reading = (
                "**rules too narrow** — the control is stated and missed"
                if defect
                else "genuinely absent from these corpora"
            )
            lines.append(
                f"| {row['label']} | 0/{pr['n']} | {pr['hits']}/{pr['n']} "
                f"({pr['pct']}%), {pr['patterns']} patterns | {reading} |"
            )
        lines += [
            "",
            "Where the reading is *genuinely absent*, note what that says about",
            "the corpora rather than only about the rules: both collections are",
            "dominated by agentic coding and assistant prompts, so controls",
            "belonging to retrieval-grounded systems are expected to be rare",
            "here. A different corpus would move these numbers.",
            "",
        ]

    lines += [
        "",
        "## What this does not show",
        "",
        "- Coverage is not quality. A separation here means production-labeled prompts",
        "  **write more controls down**, not that they are better written or",
        "  that the agents obey them.",
        "- Both corpora are leaked/aggregated collections of unknown",
        "  completeness. Neither is a random sample of anything.",
        "- Group membership is assigned by which repository a file came from,",
        "  not by inspection. That is the exposure this design accepts in",
        "  exchange for having no hand-labelling step to get wrong.",
        "",
        f"Self-checks: {payload['self_checks']} assertions passed. The run",
        "fails and writes nothing if any rate is unachievable at its own n, if",
        "a denominator is missing, if the interval and the p-value disagree, or",
        "if any 40-character run of input text appears in the output.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true", help="reuse the cache")
    ap.add_argument("--check", action="store_true",
                    help="fail if the committed report differs from a fresh run")
    args = ap.parse_args()

    groups: dict[str, dict] = {}
    texts: list[str] = []
    for c in CORPORA:
        root = fetch(c, offline=args.offline)
        files = collect(c, root)
        if not files:
            raise SystemExit(f"{c.key}: no files matched {c.globs}")
        print(f"{c.key}: {len(files)} files @ {c.sha[:8]}", file=sys.stderr)
        texts.extend(t for _, t in files)
        scored = score_corpus(files)
        groups[c.key] = {
            **scored,
            "files": len(files),
            "describe": describe(scored["overalls"]),
        }

    payload = {
        "ruleset": RULESET_ID,
        "seed": SEED,
        "resamples": RESAMPLES,
        "corpora": [
            {"key": c.key, "label": c.label, "url": c.url, "sha": c.sha,
             "globs": list(c.globs), "license_note": c.license_note}
            for c in CORPORA
        ],
        "groups": {
            k: {"files": v["files"], "describe": v["describe"]}
            for k, v in groups.items()
        },
        "controls": control_table(groups),
        "analysis": analyse(groups, random.Random(SEED)),
    }
    # A control matching nothing anywhere is a guaranteed zero in every score.
    # Surfacing it is the tool auditing its own instrument.
    payload["probes"] = probe_absence(texts)
    payload["never_fired"] = [
        {"control": r["control"], "label": r["label"], "dimension": r["dimension"]}
        for r in payload["controls"]
        if all(r[f"{k}_hits"] == 0 for k in payload["groups"])
    ]
    payload["self_checks"] = (
        len(payload["controls"]) * 4 + len(payload["groups"]) * 4 + 4
    )

    # Per-file scores, in the same run so the rows and the report are provably
    # the same computation. Schema is a whitelist: anything not listed here
    # cannot reach the file, which is what keeps prompt text out by
    # construction rather than by care.
    scores_payload = {
        "schema_version": "1.0",
        "ruleset": RULESET_ID,
        "package_version": __version__,
        "generated_from": {
            c.key: {"url": c.url, "sha": c.sha} for c in CORPORA
        },
        "disclaimer": (
            "Coverage counts which of 23 controls the prompt TEXT states. It is "
            "not quality, not safety, not certification, and not evidence of "
            "runtime behavior. A low score means the text is silent on a "
            "control, not that the product lacks it."
        ),
        "controls": sorted(c.key for cs in CONCEPTS.values() for c in cs),
        "files": [
            {"corpus": key, **row}
            for key, g in groups.items()
            for row in g["per_file"]
        ],
    }

    errs = self_check(payload, texts, extra=scores_payload)
    if errs:
        print("SELF-CHECK FAILED - nothing written:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 2

    report = render(payload)
    if args.check:
        if not REPORT.exists():
            print(f"{REPORT} missing", file=sys.stderr)
            return 1
        if REPORT.read_text(encoding="utf-8") != report:
            print(f"{REPORT} is stale - re-run the harness", file=sys.stderr)
            return 1
        print("report matches a fresh run")
        return 0

    # newline="\n" on every write: without it Windows translates to CRLF, the
    # committed LF files show as fully rewritten, and `--check` fails on a
    # run that computed identical numbers. Surfaced 2026-08-24.
    SCORES.write_text(
        json.dumps(scores_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    csv_lines = ["corpus,file_id,score,bytes,controls_fired"]
    for row in scores_payload["files"]:
        csv_lines.append(
            f"{row['corpus']},{row['file_id']},{row['score']},{row['bytes']},"
            f"\"{'|'.join(row['controls_fired'])}\""
        )
    SCORES_CSV.write_text("\n".join(csv_lines) + "\n", encoding="utf-8",
                          newline="\n")

    REPORT.write_text(report, encoding="utf-8", newline="\n")
    DATA.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")
    a = payload["analysis"]
    print(f"delta={a['delta']} p={a['p_value']} CI={a['ci95']}", file=sys.stderr)
    print(f"wrote {REPORT.relative_to(REPO)} and {DATA.relative_to(REPO)}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
