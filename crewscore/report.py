"""Self-contained HTML report, SVG badge, and share text for CrewScore."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from xml.sax.saxutils import escape as xml_escape

from crewscore import __version__
from crewscore.scoring import DIMENSIONS, RULESET_ID, ScoreResult

HOMEPAGE = "https://crewscore.ai"

# Tier colors aligned with index.html score classes
_TIER_HEX = {
    "green": "#10b981",
    "yellow": "#eab308",
    "dark_orange": "#f59e0b",
    "orange": "#f59e0b",
    "red": "#ef4444",
}


def _score_color_hex(overall: int) -> str:
    if overall >= 90:
        return _TIER_HEX["green"]
    if overall >= 70:
        return _TIER_HEX["yellow"]
    if overall >= 50:
        return _TIER_HEX["dark_orange"]
    return _TIER_HEX["red"]


def _bar_color(score: int) -> str:
    return _score_color_hex(score)


def share_text(result: ScoreResult) -> str:
    """One-line share copy with overall score and product URL."""
    if not result.governance_applicable:
        # Never publish a governance grade for a coding-agent config file.
        return (
            f"My agent config scored {result.tier} on CrewScore — "
            f"offline configuration-smell scan. {HOMEPAGE}"
        )
    # Coverage, not quality: the score says which guardrails are written down,
    # not that the agent is production-ready. See docs/validation.md.
    return (
        f"My AI agent scored {result.overall}/100 on CrewScore "
        f"({result.tier}) — offline guardrail coverage scan. "
        f"{HOMEPAGE}"
    )


def _smell_value(smell_count: int) -> str:
    """Badge/headline text for coding-agent config — a count, never a grade."""
    if smell_count <= 0:
        return "config: clean"
    if smell_count == 1:
        return "config: 1 smell"
    return f"config: {smell_count} smells"


def _smell_color_hex(smell_count: int) -> str:
    """Smells are advisory, so the scale stops at amber — never a red fail."""
    if smell_count <= 0:
        return _TIER_HEX["green"]
    if smell_count <= 2:
        return _TIER_HEX["yellow"]
    return _TIER_HEX["dark_orange"]


def render_badge_svg(result: ScoreResult) -> str:
    """Shields-style SVG badge: CrewScore | {score}/100 colored by tier.

    Coding-agent config gets `config: N smells` instead — a badge reading
    `0/100` on an AGENTS.md is the governance grade this artifact is exempt from.
    """
    label = "CrewScore"
    if result.governance_applicable:
        value = f"{result.overall}/100"
        color = _score_color_hex(result.overall)
        value_w = 54
    else:
        value = _smell_value(len(result.smells))
        color = _smell_color_hex(len(result.smells))
        # Verdana at 11px runs ~7px/char; pad so the longer text still fits.
        value_w = max(54, 7 * len(value) + 16)

    # Approximate widths for monospace-ish badge layout
    label_w = 78
    total_w = label_w + value_w
    label_x = label_w / 2
    value_x = label_w + value_w / 2

    label_esc = xml_escape(label)
    value_esc = xml_escape(value)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="20" '
        f'role="img" aria-label="{label_esc}: {value_esc}">'
        f"<title>{label_esc}: {value_esc}</title>"
        f'<linearGradient id="s" x2="0" y2="100%">'
        f'<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
        f'<stop offset="1" stop-opacity=".1"/>'
        f"</linearGradient>"
        f'<clipPath id="r"><rect width="{total_w}" height="20" rx="3" fill="#fff"/></clipPath>'
        f'<g clip-path="url(#r)">'
        f'<rect width="{label_w}" height="20" fill="#555"/>'
        f'<rect x="{label_w}" width="{value_w}" height="20" fill="{color}"/>'
        f'<rect width="{total_w}" height="20" fill="url(#s)"/>'
        f"</g>"
        f'<g fill="#fff" text-anchor="middle" '
        f'font-family="Verdana,Geneva,DejaVu Sans,sans-serif" '
        f'font-size="11">'
        f'<text x="{label_x}" y="14">{label_esc}</text>'
        f'<text x="{value_x}" y="14">{value_esc}</text>'
        f"</g>"
        f"</svg>"
    )


_BASE_CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'SF Mono',SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace;
background:#0f0f1a;color:#e2e8f0;min-height:100vh;padding:2rem 1rem;
display:flex;flex-direction:column;align-items:center}
.container{max-width:640px;width:100%}
h1{font-size:1.75rem;color:#fff;text-align:center;margin-bottom:0.25rem}
.subtitle{text-align:center;color:#94a3b8;font-size:0.85rem;margin-bottom:1.5rem}
.card{background:#1a1f2e;border:1px solid #334155;border-radius:12px;padding:1.5rem}
.score-big{font-size:3rem;font-weight:bold;text-align:center;margin:0.5rem 0}
.tier{text-align:center;font-size:1.05rem;font-weight:bold;margin-bottom:1rem}
.meta{text-align:center;font-size:0.75rem;color:#64748b;margin-bottom:1.25rem}
.disclaimer{margin-top:1.25rem;padding:0.75rem;background:#0f0f1a;border:1px solid #334155;
border-radius:8px;font-size:0.75rem;color:#94a3b8;line-height:1.45}
.footer{margin-top:1.25rem;text-align:center;font-size:0.7rem;color:#475569;line-height:1.5}
.footer a{color:#3b82f6;text-decoration:none}"""

_DIM_CSS = """.dim-row{display:flex;align-items:center;gap:0.5rem;margin:0.45rem 0;font-size:0.75rem}
.dim-label{width:200px;color:#94a3b8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dim-bar{flex:1;height:8px;background:#1e293b;border-radius:4px;overflow:hidden}
.dim-fill{height:100%;border-radius:4px}
.dim-score{width:55px;text-align:right;color:#64748b}
.findings{margin-top:1rem;font-size:0.72rem;color:#94a3b8;text-align:left}
.findings h2{color:#e2e8f0;font-size:0.85rem;margin-bottom:0.5rem}
.findings h3{color:#cbd5e1;font-size:0.78rem;margin:0.65rem 0 0.25rem}
.findings ul{padding-left:1.1rem;margin:0.2rem 0}
.findings li{margin:0.2rem 0}
.findings .matched{color:#34d399}
.findings .missing{color:#f87171}
.findings code{color:#93c5fd;font-size:0.7rem}"""

_SMELL_CSS = """.smells{margin-top:1rem;font-size:0.75rem;color:#94a3b8;text-align:left}
.smells h2{color:#e2e8f0;font-size:0.85rem;margin-bottom:0.5rem}
.smells ul{padding-left:1.1rem;margin:0.2rem 0}
.smells li{margin:0.55rem 0}
.smells strong{color:#eab308}
.smells code{color:#93c5fd;font-size:0.7rem}
.smell-meta{color:#64748b;font-size:0.68rem}"""


def _document(
    *,
    head_title: str,
    subtitle: str,
    extra_css: str,
    card_html: str,
    ruleset: str,
    version: str,
    ts: str,
) -> str:
    """Shared self-contained page shell (inline CSS, no scripts, no CDN)."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{head_title}</title>
<style>
{_BASE_CSS}
{extra_css}
</style>
</head>
<body>
<div class="container">
  <h1>CrewScore</h1>
  <p class="subtitle">{subtitle}</p>
  <div class="card">
{card_html}
  </div>
  <div class="footer">
    CrewScore v{version} · {ruleset} · Generated {ts}<br>
    <a href="{HOMEPAGE}">crewscore.ai</a>
  </div>
</div>
</body>
</html>
"""


def _render_config_html(result: ScoreResult, *, ts: str) -> str:
    """Scorecard for coding-agent config: smells only, no governance grade.

    No dimension bars, no 0-100 headline, and no `15+85*matches` formula —
    none of those describe how this artifact was judged.
    """
    count = len(result.smells)
    color = _smell_color_hex(count)
    headline = escape(_smell_value(count).removeprefix("config: "))
    tier = escape(result.tier)
    source = escape(result.source)
    ruleset = escape(getattr(result, "ruleset", None) or RULESET_ID)

    if result.smells:
        parts = ['<div class="smells"><h2>Configuration smells</h2><ul>']
        for s in result.smells:
            parts.append(
                f"<li><strong>{escape(str(s.get('name', '?')))}</strong> "
                f"<code>{escape(str(s.get('smell_id', '')))}</code><br>"
                f"{escape(str(s.get('detail', '')))}<br>"
                f'<span class="smell-meta">heuristic: '
                f"{escape(str(s.get('heuristic', '')))} · "
                f"{escape(str(s.get('paper_prevalence', '')))}</span></li>"
            )
        parts.append("</ul></div>")
        smells_html = "\n".join(parts)
    else:
        smells_html = (
            '<div class="smells"><h2>Configuration smells</h2>'
            "<p>No configuration smells detected.</p></div>"
        )

    card_html = f"""    <div class="score-big" style="color:{color}">{headline}</div>
    <div class="tier" style="color:{color}">{tier}</div>
    <div class="meta">Ruleset: {ruleset} · Artifact: coding-agent config · Source: {source}</div>
    {smells_html}
    <div class="disclaimer">
      <strong>Not a governance grade.</strong> This is repo guidance for a coding
      agent, so it is judged on configuration smells
      (<a href="https://arxiv.org/abs/2606.15828">arXiv:2606.15828</a>), not the
      8 production-governance dimensions. Across that paper's 100-repo corpus the
      governance ruleset put every such file in the worst tier — the number says
      nothing here. Smells are advisory and never folded into a score.
    </div>"""

    return _document(
        head_title=f"CrewScore — {tier}",
        subtitle="Coding-agent config report (configuration smells)",
        extra_css=_SMELL_CSS,
        card_html=card_html,
        ruleset=ruleset,
        version=escape(__version__),
        ts=escape(ts),
    )


def render_html_report(
    result: ScoreResult,
    *,
    generated_at: str | None = None,
    findings: list[dict] | None = None,
) -> str:
    """Self-contained dark HTML scorecard (inline CSS, no scripts/CDN).

    Includes ruleset, formula, and optional open rule-id findings — not a black box.
    Coding-agent config takes the smell scorecard instead; the governance
    dimensions are not a verdict on that artifact.
    """
    if generated_at is None:
        generated_at = (
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        )

    if not result.governance_applicable:
        return _render_config_html(result, ts=generated_at)

    color = _score_color_hex(result.overall)
    overall = result.overall
    tier = escape(result.tier)
    mode = escape(result.mode)
    source = escape(result.source)
    version = escape(__version__)
    ruleset = escape(getattr(result, "ruleset", None) or RULESET_ID)
    ts = escape(generated_at)

    rows: list[str] = []
    for label, key in DIMENSIONS:
        score = result.dimensions.get(key, 0)
        bar_color = _bar_color(score)
        rows.append(
            f'<div class="dim-row">'
            f'<span class="dim-label">{escape(label)}</span>'
            f'<div class="dim-bar">'
            f'<div class="dim-fill" style="width:{score}%;background:{bar_color}"></div>'
            f"</div>"
            f'<span class="dim-score">{score}/100</span>'
            f"</div>"
        )
    dim_html = "\n".join(rows)

    findings_html = ""
    if findings:
        parts: list[str] = ['<div class="findings"><h2>Open findings (rule IDs)</h2>']
        by_dim: dict[str, list[dict]] = {}
        for f in findings:
            by_dim.setdefault(f.get("dimension", "?"), []).append(f)
        for label, key in DIMENSIONS:
            items = by_dim.get(key, [])
            if not items:
                continue
            parts.append(f"<h3>{escape(label)} <code>{escape(key)}</code></h3><ul>")
            for f in items:
                rid = f.get("rule_id") or ""
                status = f.get("status") or ""
                reason = f.get("pattern_or_reason") or ""
                snippet = f.get("snippet")
                detail = snippet or reason
                rid_s = f"<code>{escape(str(rid))}</code> " if rid else ""
                parts.append(
                    f'<li class="{escape(status)}">'
                    f"<strong>{escape(status)}</strong> {rid_s}{escape(str(detail))}"
                    f"</li>"
                )
            parts.append("</ul>")
        parts.append("</div>")
        findings_html = "\n".join(parts)

    card_html = f"""    <div class="score-big" style="color:{color}">{overall}/100</div>
    <div class="tier" style="color:{color}">{tier}</div>
    <div class="meta">Ruleset: {ruleset} · Mode: {mode} · Source: {source}</div>
    {dim_html}
    <div class="disclaimer">
      <strong>Not a black box.</strong> Deterministic regex on prompt text.
      Dimension score = min(100, round(15+85×matches/total_rules)); overall = mean of 8 dims.
      List every rule with <code>crewscore rules --json</code>.
      Not live red-teaming, not runtime proof, not a certification.
    </div>
    {findings_html}"""

    return _document(
        head_title=f"CrewScore — {overall}/100",
        subtitle="Structural hygiene report (open rules)",
        extra_css=_DIM_CSS,
        card_html=card_html,
        ruleset=ruleset,
        version=version,
        ts=ts,
    )
