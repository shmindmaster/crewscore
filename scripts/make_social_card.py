"""Generate social / Open Graph / GitHub preview imagery for CrewScore.

    py scripts/make_social_card.py

Writes:
  docs/social-card.png          (1200x630 — og:image, Twitter, GitHub)
  docs/github-banner.png        (1280x640 — README / social)
  assets/brand/apple-touch-icon.png  (180x180)
  favicon.ico                   (16/32 multi-size)

Numbers on cards come from the live catalog and validation corpus JSON —
never hand-typed shock stats.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from crewscore.scorers.structural_analysis import CONCEPT_COUNT

ROOT = Path(__file__).resolve().parents[1]
OUT_SOCIAL = ROOT / "docs" / "social-card.png"
OUT_BANNER = ROOT / "docs" / "github-banner.png"
OUT_APPLE = ROOT / "assets" / "brand" / "apple-touch-icon.png"
OUT_ICO = ROOT / "favicon.ico"
CORPUS_JSON = ROOT / "docs" / "validation-corpus.json"

# Brand tokens (match assets/site.css light/dark greens)
INK = (14, 22, 18)
PANEL = (23, 32, 27)
PANEL2 = (32, 43, 36)
BORDER = (64, 81, 71)
WHITE = (238, 244, 239)
MUTED = (177, 188, 180)
DIM = (130, 145, 136)
MINT = (111, 218, 166)
MINT_SOFT = (163, 237, 196)
FOREST = (11, 79, 51)
FOREST_DEEP = (15, 63, 43)
WARN = (237, 204, 122)

FONT_DIRS = [
    Path(r"C:\Windows\Fonts"),
    Path("/usr/share/fonts"),
    Path("/Library/Fonts"),
]
CANDIDATES = {
    "bold": ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"],
    "regular": ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "Arial.ttf"],
    "mono": ["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf", "Courier New.ttf"],
}


def load(kind: str, size: int) -> ImageFont.ImageFont:
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


def production_median() -> int | None:
    if not CORPUS_JSON.exists():
        return None
    data = json.loads(CORPUS_JSON.read_text(encoding="utf-8"))
    try:
        return int(data["groups"]["production"]["describe"]["median"])
    except (KeyError, TypeError, ValueError):
        return None


def draw_logo_mark(d: ImageDraw.ImageDraw, x: int, y: int, size: int = 56) -> None:
    """Coverage-bars mark — same idea as assets/brand/logo-mark.svg."""
    r = max(8, size // 4)
    d.rounded_rectangle([x, y, x + size, y + size], radius=r, fill=FOREST)
    pad = size // 5
    bar_h = max(3, size // 9)
    gap = max(2, size // 12)
    top = y + pad
    full_w = size - 2 * pad
    fills = [0.78, 0.50, 0.28, 0.0]
    for i, frac in enumerate(fills):
        by = top + i * (bar_h + gap)
        d.rounded_rectangle(
            [x + pad, by, x + pad + full_w, by + bar_h],
            radius=bar_h // 2,
            fill=FOREST_DEEP,
        )
        if frac > 0:
            d.rounded_rectangle(
                [x + pad, by, x + pad + int(full_w * frac), by + bar_h],
                radius=bar_h // 2,
                fill=MINT if i < 2 else MINT_SOFT,
            )
        else:
            # dashed gap bar (missing control)
            d.rounded_rectangle(
                [x + pad, by, x + pad + full_w, by + bar_h],
                radius=bar_h // 2,
                outline=WARN,
                width=max(1, size // 32),
            )


def paint_social(path: Path, *, w: int, h: int) -> None:
    count = CONCEPT_COUNT
    median = production_median()

    img = Image.new("RGB", (w, h), INK)
    d = ImageDraw.Draw(img)

    # Soft vignette panel
    margin = 40 if w >= 1200 else 28
    d.rounded_rectangle(
        [margin, margin, w - margin, h - margin],
        radius=28,
        fill=PANEL,
        outline=BORDER,
        width=2,
    )

    # Accent strip on left
    d.rounded_rectangle(
        [margin, margin, margin + 10, h - margin],
        radius=6,
        fill=MINT,
    )

    f_brand = load("bold", 54 if w >= 1200 else 44)
    f_tag = load("regular", 28 if w >= 1200 else 24)
    f_stat = load("bold", 120 if w >= 1200 else 96)
    f_label = load("regular", 26 if w >= 1200 else 22)
    f_foot = load("mono", 22 if w >= 1200 else 18)
    f_small = load("regular", 20)

    lx, ly = margin + 48, margin + 42
    draw_logo_mark(d, lx, ly, 64)
    d.text((lx + 80, ly + 12), "CrewScore", font=f_brand, fill=WHITE)

    d.text(
        (lx, ly + 90),
        "Find the safety rules your AI agent prompt forgot.",
        font=f_tag,
        fill=MUTED,
    )

    # Big checklist size
    d.text((lx, ly + 160), str(count), font=f_stat, fill=MINT)
    d.text(
        (lx + (160 if count < 100 else 200), ly + 210),
        "public controls",
        font=f_label,
        fill=MUTED,
    )
    d.text(
        (lx, ly + 300),
        "injection · human approval · cost · stop · and more",
        font=f_label,
        fill=DIM,
    )
    d.text(
        (lx, ly + 340),
        "See which ones yours is missing. Coverage, not a safety grade.",
        font=f_label,
        fill=MUTED,
    )

    # Right shock panel
    panel_x0 = w - margin - 340
    panel_y0 = margin + 150
    d.rounded_rectangle(
        [panel_x0, panel_y0, w - margin - 36, h - margin - 90],
        radius=18,
        fill=PANEL2,
        outline=BORDER,
        width=1,
    )
    if median is not None:
        d.text(
            (panel_x0 + 28, panel_y0 + 28),
            "Production median",
            font=f_small,
            fill=DIM,
        )
        d.text(
            (panel_x0 + 28, panel_y0 + 58),
            f"{median}/100",
            font=load("bold", 56),
            fill=WARN,
        )
        d.text(
            (panel_x0 + 28, panel_y0 + 130),
            "among 83 production",
            font=f_small,
            fill=MUTED,
        )
        d.text(
            (panel_x0 + 28, panel_y0 + 158),
            "agent prompts (356 total)",
            font=f_small,
            fill=MUTED,
        )
        d.text(
            (panel_x0 + 28, panel_y0 + 200),
            "Not a quality ranking.",
            font=f_small,
            fill=DIM,
        )
    else:
        d.text(
            (panel_x0 + 28, panel_y0 + 40),
            f"{count} controls",
            font=load("bold", 40),
            fill=MINT,
        )
        d.text(
            (panel_x0 + 28, panel_y0 + 100),
            "offline · open rules",
            font=f_small,
            fill=MUTED,
        )

    d.line(
        [lx, h - margin - 56, w - margin - 48, h - margin - 56],
        fill=BORDER,
        width=1,
    )
    d.text((lx, h - margin - 42), "crewscore.ai", font=f_foot, fill=DIM)
    d.text((lx + 200, h - margin - 42), "pip install crewscore", font=f_foot, fill=DIM)
    d.text(
        (lx + 480, h - margin - 42),
        "offline · no API key · local browser",
        font=f_foot,
        fill=DIM,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)
    print(f"wrote {path} ({path.stat().st_size // 1024} KB)")


def paint_icon(path: Path, size: int = 180) -> None:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Full-bleed rounded tile
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 4, fill=FOREST)
    pad = size // 5
    bar_h = max(4, size // 10)
    gap = max(3, size // 14)
    top = pad + size // 20
    full_w = size - 2 * pad
    fills = [0.78, 0.50, 0.28]
    for i, frac in enumerate(fills):
        by = top + i * (bar_h + gap)
        d.rounded_rectangle(
            [pad, by, pad + full_w, by + bar_h],
            radius=bar_h // 2,
            fill=FOREST_DEEP,
        )
        d.rounded_rectangle(
            [pad, by, pad + int(full_w * frac), by + bar_h],
            radius=bar_h // 2,
            fill=MINT if i == 0 else MINT_SOFT,
        )
    # Missing control (dashed outline)
    by = top + 3 * (bar_h + gap)
    d.rounded_rectangle(
        [pad, by, pad + full_w, by + bar_h],
        radius=bar_h // 2,
        outline=WARN,
        width=max(2, size // 48),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)
    print(f"wrote {path}")


def paint_favicon_ico(path: Path) -> None:
    sizes = [16, 32, 48]
    images: list[Image.Image] = []
    for s in sizes:
        canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(canvas)
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=max(2, s // 4), fill=FOREST)
        pad = max(2, s // 5)
        bar_h = max(2, s // 8)
        gap = max(1, s // 12)
        top = pad
        full_w = s - 2 * pad
        for i, frac in enumerate((0.8, 0.45, 0.25)):
            by = top + i * (bar_h + gap)
            if by + bar_h > s - 1:
                break
            d.rounded_rectangle(
                [pad, by, pad + full_w, by + bar_h],
                radius=1,
                fill=FOREST_DEEP,
            )
            d.rounded_rectangle(
                [pad, by, pad + max(1, int(full_w * frac)), by + bar_h],
                radius=1,
                fill=MINT,
            )
        images.append(canvas)
    path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        path,
        format="ICO",
        sizes=[(im.width, im.height) for im in images],
        append_images=images[1:],
    )
    print(f"wrote {path}")


def main() -> int:
    paint_social(OUT_SOCIAL, w=1200, h=630)
    paint_social(OUT_BANNER, w=1280, h=640)
    paint_icon(OUT_APPLE, 180)
    paint_icon(ROOT / "assets" / "brand" / "icon-512.png", 512)
    paint_favicon_ico(OUT_ICO)
    print(f"controls={CONCEPT_COUNT} production_median={production_median()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
