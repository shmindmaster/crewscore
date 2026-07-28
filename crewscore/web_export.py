"""Export structural scorer data for the static web engine."""

from __future__ import annotations

import json

from crewscore import __version__
from crewscore.profiles import (
    CODING_AGENT_CONFIG,
    PROFILE_LABELS,
    PROFILES,
    SYSTEM_PROMPT,
)
from crewscore.scoring import DIMENSIONS, RULESET_ID
from crewscore.scorers.fix_patterns import FIX_TEMPLATES
from crewscore.scorers.structural_analysis import DIMENSION_SIGNAL_LABELS, SCORER_MAP
from crewscore.smells import CITATION, CONTEXT_BLOAT_MAX_LINES, SMELL_CATALOG
from crewscore.vendor_scorecard import QUESTIONS

# Two of the three offline smell detectors need context a browser tab does not
# have. Naming them in the payload keeps the UI honest: a clean browser result
# is a partial check, not a clean bill of health.
BROWSER_UNDETECTABLE_SMELLS: list[dict[str, str]] = [
    {
        "smell_id": "smell.init_fossilization",
        "reason": "needs git history for the file — run the CLI",
    },
    {
        "smell_id": "smell.lint_leakage",
        "reason": "needs the rest of the repo (linter/formatter configs) — run the CLI",
    },
]

JS_RUNTIME = r"""
/** CrewScore browser scorer — generated from Python. Do not edit by hand. */
(function (global) {
  const ENGINE = __PAYLOAD__;

  function scoreFromMatchCount(matches, total) {
    if (!total || matches === 0) return 0;
    const raw = matches / total;
    return Math.min(100, Math.round(15 + raw * 85));
  }

  function safeRegExp(pattern) {
    try {
      return new RegExp(pattern, "i");
    } catch (e) {
      return null;
    }
  }

  function matchPatterns(promptLower, patterns) {
    const hits = [];
    for (const entry of patterns) {
      // Support [rule_id, pattern] tuples and bare pattern strings.
      const ruleId = Array.isArray(entry) ? entry[0] : null;
      const pattern = Array.isArray(entry) ? entry[1] : entry;
      const re = safeRegExp(pattern);
      if (!re) continue;
      const m = promptLower.match(re);
      if (m) {
        let snip = m[0].replace(/\s+/g, " ");
        if (snip.length > 120) snip = snip.slice(0, 119) + "…";
        hits.push({ ruleId, pattern, snippet: snip });
      }
    }
    return hits;
  }

  function detectTemplateBoilerplate(prompt) {
    if (!prompt) return [];
    const markers = [
      "CrewScore",
      "## Prompt Injection Defense",
      "# Guardrails (Applied by CrewScore)",
      "## Additional Guardrails (Applied by CrewScore)",
    ];
    const templates = ENGINE.fix_templates || {};
    Object.values(templates).forEach((t) => {
      const line = String(t)
        .split("\n")
        .map((l) => l.trim())
        .find((l) => l.startsWith("## "));
      if (line) markers.push(line);
    });
    let hits = 0;
    for (const m of markers) {
      if (prompt.includes(m)) hits += 1;
    }
    if ((prompt.includes("CrewScore") && hits >= 2) || hits >= 3) {
      return ["template_boilerplate_detected"];
    }
    return [];
  }

  // The length bonus was removed in ruleset 0.3.0 — length is a cost, not a
  // virtue, and it was never part of the published formula. See
  // crewscore/scorers/structural_analysis.py for the full rationale.

  function analyzeWithFindings(systemPrompt) {
    const dimOrder = ENGINE.dimensions.map((d) => d.key);
    if (!systemPrompt || !String(systemPrompt).trim()) {
      const scores = {};
      const findings = [];
      for (const key of dimOrder) {
        scores[key] = 0;
        const signals = ENGINE.signal_labels[key] || [];
        for (const s of signals.slice(0, 3)) {
          const entry = {
            dimension: key,
            status: "missing",
            pattern_or_reason: s.label,
            snippet: null,
          };
          if (s.rule_id) entry.rule_id = s.rule_id;
          findings.push(entry);
        }
      }
      return {
        scores,
        findings,
        overall: 0,
        ruleset: ENGINE.ruleset,
        warnings: [],
      };
    }

    const promptLower = String(systemPrompt).toLowerCase();
    const scores = {};
    const findings = [];

    for (const key of dimOrder) {
      const patterns = ENGINE.patterns[key] || [];
      const hits = matchPatterns(promptLower, patterns);
      scores[key] = scoreFromMatchCount(hits.length, patterns.length);

      for (const h of hits.slice(0, 3)) {
        const entry = {
          dimension: key,
          status: "matched",
          pattern_or_reason: h.pattern,
          snippet: h.snippet,
        };
        if (h.ruleId) entry.rule_id = h.ruleId;
        findings.push(entry);
      }

      let missingCount = 0;
      for (const s of ENGINE.signal_labels[key] || []) {
        if (missingCount >= 3) break;
        const re = safeRegExp(s.pattern);
        const matched = re ? re.test(promptLower) : false;
        if (matched) continue;
        const entry = {
          dimension: key,
          status: "missing",
          pattern_or_reason: s.label,
          snippet: null,
        };
        if (s.rule_id) entry.rule_id = s.rule_id;
        findings.push(entry);
        missingCount += 1;
      }
      if (!hits.length && missingCount === 0) {
        findings.push({
          dimension: key,
          status: "missing",
          pattern_or_reason: "No " + key + " guardrail signals detected",
          snippet: null,
        });
      }
    }

    const vals = dimOrder.map((k) => scores[k]);
    const overall = vals.length
      ? Math.floor(vals.reduce((a, b) => a + b, 0) / vals.length)
      : 0;
    const warnings = detectTemplateBoilerplate(String(systemPrompt));
    return {
      scores,
      findings,
      overall,
      ruleset: ENGINE.ruleset,
      warnings,
    };
  }

  function analyze(systemPrompt) {
    return analyzeWithFindings(systemPrompt).scores;
  }

  /** Mirrors Python str.splitlines() so the line count is the same number. */
  function splitLines(text) {
    if (!text) return [];
    const parts = String(text).split(
      /\r\n|[\n\r\u000b\u000c\u001c\u001d\u001e\u0085\u2028\u2029]/
    );
    // Python treats a trailing terminator as ending the last line, not as
    // starting an empty one: "a\n".splitlines() == ["a"].
    if (parts.length && parts[parts.length - 1] === "") parts.pop();
    return parts;
  }

  /**
   * Context Bloat — the only one of the three configuration smells a browser
   * can honestly run. Threshold and wording are the published heuristic from
   * crewscore/smells.py; do not tune them here.
   */
  function detectContextBloat(text) {
    if (!text) return null;
    const lines = splitLines(text).length;
    const max = ENGINE.context_bloat_max_lines;
    if (lines < max) return null;
    const meta = (ENGINE.smell_catalog || {})["smell.context_bloat"] || {};
    return {
      smell_id: "smell.context_bloat",
      name: meta.name,
      detail:
        lines +
        " lines (threshold " +
        max +
        "). Long files raise token cost and reduce adherence to the rules " +
        "that matter.",
      heuristic: meta.heuristic,
      paper_prevalence: meta.paper_prevalence,
      citation: ENGINE.smell_citation,
      deterministic: meta.deterministic,
      approximates_paper: meta.approximates_paper,
      // Advisory only — never folded into any number. See crewscore/smells.py.
      affects_score: false,
      line_count: lines,
    };
  }

  /** Mirrors crewscore.scoring.config_tier — smell counts, never a 0-100 grade. */
  function configTier(smellCount) {
    if (!smellCount || smellCount <= 0) return "CONFIG: NO SMELLS DETECTED";
    if (smellCount === 1) return "CONFIG: 1 SMELL";
    return "CONFIG: " + smellCount + " SMELLS";
  }

  /** Mirrors crewscore.profiles.governance_applies. */
  function governanceApplies(profile) {
    return profile !== ENGINE.config_profile;
  }

  function profileLabel(profile) {
    const hit = (ENGINE.profiles || []).find((p) => p.key === profile);
    return hit ? hit.label : profile;
  }

  /**
   * Score an artifact the user has *declared* the type of.
   *
   * The CLI classifies by filename (crewscore/profiles.py::classify_path). A
   * browser has no filename, and sniffing the pasted text would be a guess
   * dressed up as a measurement — so the profile is declared, never inferred.
   *
   * Coding-agent config gets no governance number, no dimensions and no
   * governance tier: measured on the arXiv:2606.15828 corpus the governance
   * ruleset put 100/100 real config files in the worst tier, so the number
   * carries no information for that artifact.
   */
  function analyzeArtifact(text, profile) {
    const declared = profile || ENGINE.default_profile;
    if (governanceApplies(declared)) {
      const result = analyzeWithFindings(text);
      result.profile = declared;
      result.governance_applicable = true;
      return result;
    }
    const smells = [];
    const bloat = detectContextBloat(text);
    if (bloat) smells.push(bloat);
    return {
      profile: declared,
      governance_applicable: false,
      tier: configTier(smells.length),
      smells,
      // Two detectors cannot run here; a clean result is a partial check.
      undetectable: ENGINE.browser_undetectable_smells || [],
      detectors_run: 1,
      detectors_total: 3,
      ruleset: ENGINE.ruleset,
    };
  }

  function scoreTier(overall) {
    if (overall >= 90) return { n: "STRUCTURAL: STRONG", c: "score-green" };
    if (overall >= 70) return { n: "STRUCTURAL: OK WITH GAPS", c: "score-yellow" };
    if (overall >= 50) return { n: "STRUCTURAL: WEAK", c: "score-orange" };
    return { n: "STRUCTURAL: CRITICAL GAPS", c: "score-red" };
  }

  function vendorTier(overall) {
    if (overall >= 80) return { n: "TRUSTED", c: "score-green" };
    if (overall >= 50) return { n: "CAUTION", c: "score-yellow" };
    if (overall >= 30) return { n: "HIGH RISK", c: "score-orange" };
    return { n: "RED FLAG", c: "score-red" };
  }

  /** answers: array of 'yes'|'no'|'dk' — same points as CLI (y=10, dk=3, no=0). */
  function scoreVendor(answers) {
    const SCORE = { yes: 10, dk: 3, no: 0 };
    let total = 0;
    const redFlags = [];
    const critical = new Set(ENGINE.vendor_critical_keys);
    (answers || []).forEach((a, i) => {
      const norm = (a || "no").toLowerCase();
      const pts = SCORE[norm] !== undefined ? SCORE[norm] : 0;
      total += pts;
      const q = ENGINE.vendor_questions[i] || "";
      const key = ENGINE.vendor_keys[i] || "";
      if (norm === "no" || (norm === "dk" && critical.has(key))) {
        redFlags.push(q.replace(/\?$/, ""));
      }
    });
    return { score: total, tier: vendorTier(total), redFlags };
  }

  /** Same threshold as CLI generate_fixes: score < 70. */
  function generateFixes(scores) {
    const fixes = {};
    const templates = ENGINE.fix_templates || {};
    Object.keys(scores || {}).forEach((dim) => {
      if ((scores[dim] || 0) < 70 && templates[dim]) {
        fixes[dim] = templates[dim];
      }
    });
    return fixes;
  }

  function applyFixes(systemPrompt, fixes) {
    const keys = Object.keys(fixes || {});
    if (!keys.length) return systemPrompt || "";
    const block = keys.map((k) => fixes[k]).join("\n\n");
    let enhanced = (systemPrompt || "").replace(/\s+$/, "");
    if (!enhanced.includes("## Guardrails") && !enhanced.includes("## Safety")) {
      enhanced +=
        "\n\n---\n\n# Guardrails (Applied by CrewScore)\n\n" + block + "\n";
    } else {
      enhanced +=
        "\n\n## Additional Guardrails (Applied by CrewScore)\n\n" + block + "\n";
    }
    return enhanced;
  }

  function fixAndRescore(systemPrompt) {
    const before = analyzeWithFindings(systemPrompt);
    const fixes = generateFixes(before.scores);
    const enhanced = applyFixes(systemPrompt, fixes);
    const after = analyzeWithFindings(enhanced);
    return {
      before,
      after,
      fixes,
      enhanced,
      delta: after.overall - before.overall,
    };
  }

  global.CrewScoreEngine = {
    ENGINE,
    ruleset: ENGINE.ruleset,
    analyze,
    analyzeWithFindings,
    analyzeArtifact,
    detectContextBloat,
    configTier,
    governanceApplies,
    profileLabel,
    profiles: ENGINE.profiles,
    defaultProfile: ENGINE.default_profile,
    configProfile: ENGINE.config_profile,
    contextBloatMaxLines: ENGINE.context_bloat_max_lines,
    scoreTier,
    vendorTier,
    scoreVendor,
    generateFixes,
    applyFixes,
    fixAndRescore,
    dimensions: ENGINE.dimensions,
    vendorQuestions: ENGINE.vendor_questions,
    // Transparency: every rule lives in ENGINE.patterns as [rule_id, regex]
    openScoring: true,
  };
})(typeof window !== "undefined" ? window : globalThis);
"""


def build_payload() -> dict:
    dim_order = [key for _, key in DIMENSIONS]
    # Flatten rule_id → pattern for signal labels.
    pattern_to_rule: dict[str, str] = {}
    for key in dim_order:
        for rule_id, pattern in SCORER_MAP[key]:
            pattern_to_rule[pattern] = rule_id

    return {
        "version": __version__,
        "ruleset": RULESET_ID,
        "dimensions": [{"key": key, "label": label} for label, key in DIMENSIONS],
        # patterns as [rule_id, regex] pairs for JS matchPatterns
        "patterns": {
            key: [[rule_id, pattern] for rule_id, pattern in SCORER_MAP[key]]
            for key in dim_order
        },
        "signal_labels": {
            key: [
                {
                    "pattern": p,
                    "label": lab,
                    **({"rule_id": pattern_to_rule[p]} if p in pattern_to_rule else {}),
                }
                for p, lab in DIMENSION_SIGNAL_LABELS.get(key, [])
            ]
            for key in dim_order
        },
        "fix_templates": {
            key: FIX_TEMPLATES[key].strip()
            for key in dim_order
            if key in FIX_TEMPLATES
        },
        # The browser has no filename, so the artifact type is declared by the
        # user rather than classified (crewscore/profiles.py::classify_path).
        # Inferring it from the pasted text would be a guess dressed up as a
        # measurement — the exact failure the profile split exists to prevent.
        "profiles": [
            {"key": key, "label": PROFILE_LABELS[key]} for key in PROFILES
        ],
        "default_profile": SYSTEM_PROMPT,
        "config_profile": CODING_AGENT_CONFIG,
        "context_bloat_max_lines": CONTEXT_BLOAT_MAX_LINES,
        "smell_citation": CITATION,
        "smell_catalog": {
            "smell.context_bloat": {
                **SMELL_CATALOG["smell.context_bloat"],
                "citation": CITATION,
                # Smells are advisory; folding them into a number would change
                # the meaning of every existing --threshold in consumer CI.
                "affects_score": False,
            }
        },
        "browser_undetectable_smells": [
            {
                **entry,
                "name": SMELL_CATALOG[entry["smell_id"]]["name"],
            }
            for entry in BROWSER_UNDETECTABLE_SMELLS
        ],
        "vendor_questions": [q for q, _ in QUESTIONS],
        "vendor_keys": [k for _, k in QUESTIONS],
        "vendor_critical_keys": [
            "certification",
            "audit",
            "human_override",
            "security_audit",
            "incident",
        ],
    }


def render_js(payload: dict | None = None) -> str:
    payload = payload or build_payload()
    blob = json.dumps(payload, indent=2, ensure_ascii=False)
    header = (
        "/* eslint-disable */\n"
        "/* Generated by scripts/export_web_engine.py — do not edit by hand. */\n"
    )
    return header + JS_RUNTIME.replace("__PAYLOAD__", blob)
