"""Public corpus card: screenshot-ready SVG of validation shock numbers.

Pure rendering + markdown parse. No network. Numbers come from
docs/validation-corpus.md (or any text with the same table shape).
"""

from __future__ import annotations

import re
from xml.sax.saxutils import escape as xml_escape

# Social-friendly default canvas (~Twitter/LinkedIn card proportions, not 1200x630).
_WIDTH = 800
_HEIGHT = 420

_HONESTY = "written-control coverage — not runtime proof"


def parse_validation_corpus_stats(md_text: str) -> dict:
    """Parse production / GPT-Store n+median and Cliff's delta from validation MD.

    Expects the score-distribution table and discrimination line produced by
    scripts/validate_corpus.py. Keys: production_n, production_median,
    gpt_store_n, gpt_store_median, cliffs_delta.
    """
    # Score distribution table rows (n | Median | IQR | ...).
    # Prefer the denser table over the Corpora "Files scored" table by matching
    # the Median column position (second numeric cell after the name).
    prod = re.search(
        r"\|\s*Production-labeled agent system prompts\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
        md_text,
    )
    gpt = re.search(
        r"\|\s*General-purpose GPT-Store prompts\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
        md_text,
    )
    if not prod or not gpt:
        raise ValueError(
            "could not find production-labeled / GPT-Store score-distribution rows "
            "in validation corpus markdown"
        )

    delta_m = re.search(r"Cliff's delta\s*=\s*([0-9.]+)", md_text, re.IGNORECASE)
    if not delta_m:
        raise ValueError("could not find Cliff's delta in validation corpus markdown")

    return {
        "production_n": int(prod.group(1)),
        "production_median": int(prod.group(2)),
        "gpt_store_n": int(gpt.group(1)),
        "gpt_store_median": int(gpt.group(2)),
        "cliffs_delta": float(delta_m.group(1)),
    }


def render_corpus_card_svg(
    *,
    production_n: int,
    production_median: int,
    gpt_store_n: int,
    gpt_store_median: int,
    cliffs_delta: float,
    ruleset: str = "crewscore-hygiene@0.6.0",
    homepage: str = "https://crewscore.ai",
) -> str:
    """Render a self-contained SVG card from corpus stats. Stdlib only."""
    title = "CrewScore"
    subtitle = "Coverage on publicly collected agent prompts"
    honesty = _HONESTY
    prod_label = "Production-labeled prompts"
    gpt_label = "GPT-Store prompts"
    delta_label = f"Cliff's delta = {cliffs_delta:g}"
    n_line = f"n={production_n} vs n={gpt_store_n}"
    foot = f"{ruleset}  ·  {homepage}"

    # Escape all variable text for XML safety.
    e_title = xml_escape(title)
    e_subtitle = xml_escape(subtitle)
    e_honesty = xml_escape(honesty)
    e_prod_label = xml_escape(prod_label)
    e_gpt_label = xml_escape(gpt_label)
    e_delta = xml_escape(delta_label)
    e_n_line = xml_escape(n_line)
    e_foot = xml_escape(foot)
    e_prod_med = xml_escape(str(production_median))
    e_gpt_med = xml_escape(str(gpt_store_median))
    e_prod_n = xml_escape(str(production_n))
    e_gpt_n = xml_escape(str(gpt_store_n))

    # Score bars: scale medians to a 0-100 track for visual weight.
    track_w = 280
    prod_bar = max(2, int(track_w * min(production_median, 100) / 100))
    gpt_bar = max(2, int(track_w * min(gpt_store_median, 100) / 100)) if gpt_store_median else 2

    return f'''\
<svg xmlns="http://www.w3.org/2000/svg" width="{_WIDTH}" height="{_HEIGHT}" \
viewBox="0 0 {_WIDTH} {_HEIGHT}" role="img" aria-labelledby="title desc">
  <title id="title">{e_title}: production-labeled median {e_prod_med}, GPT-Store median {e_gpt_med}</title>
  <desc id="desc">{e_honesty}. {e_prod_label} n={e_prod_n} median {e_prod_med}/100; \
{e_gpt_label} n={e_gpt_n} median {e_gpt_med}/100. {e_delta}.</desc>
  <defs>
    <style>
      .bg {{ fill: #0E1612; }}
      .panel {{ fill: #17201B; stroke: #405147; stroke-width: 1; }}
      .t {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; }}
      .white {{ fill: #EEF4EF; }}
      .muted {{ fill: #B1BCB4; }}
      .dim {{ fill: #829189; }}
      .mint {{ fill: #6FDAA6; }}
      .warn {{ fill: #EDCC7A; }}
      .track {{ fill: #202B24; }}
      .bar-prod {{ fill: #6FDAA6; }}
      .bar-gpt {{ fill: #64748b; }}
    </style>
  </defs>
  <rect class="bg" width="{_WIDTH}" height="{_HEIGHT}" rx="16"/>
  <rect class="panel" x="28" y="28" width="{_WIDTH - 56}" height="{_HEIGHT - 56}" rx="12"/>

  <text class="t white" x="56" y="78" font-size="28" font-weight="700">{e_title}</text>
  <text class="t muted" x="56" y="108" font-size="15">{e_subtitle}</text>
  <text class="t dim" x="56" y="132" font-size="13">{e_honesty}</text>

  <!-- Production-labeled column -->
  <text class="t muted" x="56" y="180" font-size="14">{e_prod_label}</text>
  <text class="t mint" x="56" y="250" font-size="64" font-weight="700">{e_prod_med}</text>
  <text class="t dim" x="56" y="278" font-size="14">/100 median  ·  n={e_prod_n}</text>
  <rect class="track" x="56" y="296" width="{track_w}" height="10" rx="4"/>
  <rect class="bar-prod" x="56" y="296" width="{prod_bar}" height="10" rx="4"/>

  <!-- GPT-Store column -->
  <text class="t muted" x="420" y="180" font-size="14">{e_gpt_label}</text>
  <text class="t warn" x="420" y="250" font-size="64" font-weight="700">{e_gpt_med}</text>
  <text class="t dim" x="420" y="278" font-size="14">/100 median  ·  n={e_gpt_n}</text>
  <rect class="track" x="420" y="296" width="{track_w}" height="10" rx="4"/>
  <rect class="bar-gpt" x="420" y="296" width="{gpt_bar}" height="10" rx="4"/>

  <text class="t muted" x="56" y="350" font-size="14">{e_delta}  ·  {e_n_line}</text>
  <text class="t dim" x="56" y="382" font-size="12">{e_foot}</text>
</svg>
'''
