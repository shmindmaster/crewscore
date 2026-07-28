"""Generate the 1200x630 social card used for og:image and GitHub's preview.

Committed as a script rather than a hand-made binary so the card can be
regenerated when the headline number or the positioning changes -- the same
reason score-engine.js is generated instead of hand-edited.

    py scripts/make_social_card.py

Writes docs/social-card.png.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from crewscore.scoring import DIMENSION_KEYS, overall_score
from crewscore.scorers.structural_analysis import SCORER_MAP

W, H = 1200, 630
BG = (15, 15, 26)
PANEL = (26, 31, 46)
BORDER = (51, 65, 85)
WHITE = (255, 255, 255)
MUTED = (148, 163, 184)
DIM = (100, 116, 139)
AMBER = (245, 158, 11)

OUT = Path(__file__).resolve().parents[1] / "docs" / "social-card.png"

# Windows ships these; fall back to PIL's bitmap font rather than failing.
FONT_DIRS = [Path(r"C:\Windows\Fonts"), Path("/usr/share/fonts"), Path("/Library/Fonts")]
CANDIDATES = {
    "bold": ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"],
    "regular": ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "Arial.ttf"],
    "mono": ["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf", "Courier New.ttf"],
}


def load(kind: str, size: int):
    for directory in FONT_DIRS:
        if not directory.exists():
            continue
        for name in CANDIDATES[kind]:
            for path in (directory / name, *directory.rglob(name)):
                if path.exists():
                    try:
                        return ImageFont.truetype(str(path), size)
                    except OSError:
                        continue
    return ImageFont.load_default()


def headline_score() -> int:
    """The number on the card is computed, never typed by hand."""

    def dim(matches: int, total: int) -> int:
        if not total or not matches:
            return 0
        return min(100, round(15 + 85 * matches / total))

    return overall_score({k: dim(1, len(SCORER_MAP[k])) for k in DIMENSION_KEYS})


def main() -> int:
    score = headline_score()

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([40, 40, W - 40, H - 40], radius=24, fill=PANEL, outline=BORDER, width=2)

    f_brand = load("bold", 62)
    f_tag = load("regular", 30)
    f_stat = load("bold", 132)
    f_stat_label = load("regular", 27)
    f_foot = load("mono", 24)

    d.text((88, 92), "CrewScore", font=f_brand, fill=WHITE)
    d.text(
        (88, 172),
        "Governance checklist for AI agent prompts",
        font=f_tag,
        fill=MUTED,
    )

    # The hook: the tool's own scale is unreachable by a well-written prompt.
    d.text((88, 268), f"{score}/100", font=f_stat, fill=AMBER)
    d.text(
        (88, 424),
        "what a prompt scores when it states all eight",
        font=f_stat_label,
        fill=MUTED,
    )
    d.text(
        (88, 458),
        "governance controls clearly. The lowest tier starts at 50.",
        font=f_stat_label,
        fill=MUTED,
    )

    d.line([88, 516, W - 88, 516], fill=BORDER, width=1)
    d.text((88, 540), "crewscore.ai", font=f_foot, fill=DIM)
    d.text((300, 540), "pip install crewscore", font=f_foot, fill=DIM)
    d.text((640, 540), "offline . deterministic . no API key", font=f_foot, fill=DIM)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB) headline={score}/100")
    return 0


if __name__ == "__main__":
    sys.exit(main())
