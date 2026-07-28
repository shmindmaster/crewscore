"""Self-contained HTML report, SVG badge, and share text for CrewScore."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from xml.sax.saxutils import escape as xml_escape

from crewscore import __version__
from crewscore.scoring import DIMENSIONS, ScoreResult

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
    return (
        f"My AI agent scored {result.overall}/100 on CrewScore "
        f"({result.tier}) — structural production-readiness scan. "
        f"{HOMEPAGE}"
    )


def render_badge_svg(result: ScoreResult) -> str:
    """Shields-style SVG badge: CrewScore | {score}/100 colored by tier."""
    label = "CrewScore"
    value = f"{result.overall}/100"
    color = _score_color_hex(result.overall)

    # Approximate widths for monospace-ish badge layout
    label_w = 78
    value_w = 54
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


def render_html_report(
    result: ScoreResult,
    *,
    generated_at: str | None = None,
) -> str:
    """Self-contained dark HTML scorecard (inline CSS, no scripts/CDN)."""
    if generated_at is None:
        generated_at = (
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        )

    color = _score_color_hex(result.overall)
    overall = result.overall
    tier = escape(result.tier)
    mode = escape(result.mode)
    source = escape(result.source)
    version = escape(__version__)
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

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CrewScore — {overall}/100</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'SF Mono',SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace;
background:#0f0f1a;color:#e2e8f0;min-height:100vh;padding:2rem 1rem;
display:flex;flex-direction:column;align-items:center}}
.container{{max-width:640px;width:100%}}
h1{{font-size:1.75rem;color:#fff;text-align:center;margin-bottom:0.25rem}}
.subtitle{{text-align:center;color:#94a3b8;font-size:0.85rem;margin-bottom:1.5rem}}
.card{{background:#1a1f2e;border:1px solid #334155;border-radius:12px;padding:1.5rem}}
.score-big{{font-size:3rem;font-weight:bold;text-align:center;color:{color};margin:0.5rem 0}}
.tier{{text-align:center;font-size:1.05rem;font-weight:bold;color:{color};margin-bottom:1rem}}
.meta{{text-align:center;font-size:0.75rem;color:#64748b;margin-bottom:1.25rem}}
.dim-row{{display:flex;align-items:center;gap:0.5rem;margin:0.45rem 0;font-size:0.75rem}}
.dim-label{{width:200px;color:#94a3b8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.dim-bar{{flex:1;height:8px;background:#1e293b;border-radius:4px;overflow:hidden}}
.dim-fill{{height:100%;border-radius:4px}}
.dim-score{{width:55px;text-align:right;color:#64748b}}
.disclaimer{{margin-top:1.25rem;padding:0.75rem;background:#0f0f1a;border:1px solid #334155;
border-radius:8px;font-size:0.75rem;color:#94a3b8;line-height:1.45}}
.footer{{margin-top:1.25rem;text-align:center;font-size:0.7rem;color:#475569;line-height:1.5}}
.footer a{{color:#3b82f6;text-decoration:none}}
</style>
</head>
<body>
<div class="container">
  <h1>CrewScore</h1>
  <p class="subtitle">Structural Production Readiness Report</p>
  <div class="card">
    <div class="score-big">{overall}/100</div>
    <div class="tier">{tier}</div>
    <div class="meta">Mode: {mode} · Source: {source}</div>
    {dim_html}
    <div class="disclaimer">
      <strong>Structural scan only</strong> — offline pattern match on prompt text.
      Not a substitute for live behavioral red-teaming or runtime proof of safety.
    </div>
  </div>
  <div class="footer">
    CrewScore v{version} · Generated {ts}<br>
    <a href="{HOMEPAGE}">crewscore.ai</a>
  </div>
</div>
</body>
</html>
"""
