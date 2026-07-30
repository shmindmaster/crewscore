"""Composite Imagine mood art with exact brand text for OG / GitHub."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from crewscore.scorers.structural_analysis import CONCEPT_COUNT

ROOT = Path(__file__).resolve().parents[1]
IMAGINE = ROOT / "assets" / "brand" / "imagine"
OUT_SOCIAL = ROOT / "docs" / "social-card.png"
OUT_BANNER = ROOT / "docs" / "github-banner.png"
OUT_APPLE = ROOT / "assets" / "brand" / "apple-touch-icon.png"
OUT_512 = ROOT / "assets" / "brand" / "icon-512.png"
OUT_HERO = ROOT / "assets" / "brand" / "hero-imagine.png"
CORPUS = ROOT / "docs" / "validation-corpus.json"

FONT_DIRS = [Path(r"C:\Windows\Fonts"), Path("/usr/share/fonts"), Path("/Library/Fonts")]
CAND = {
    "bold": ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"],
    "regular": ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"],
    "mono": ["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf"],
}


def load(kind: str, size: int):
    for d in FONT_DIRS:
        if not d.exists():
            continue
        for name in CAND[kind]:
            p = d / name
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size)
                except OSError:
                    pass
    return ImageFont.load_default()


def median() -> int | None:
    if not CORPUS.exists():
        return None
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    try:
        return int(data["groups"]["production"]["describe"]["median"])
    except Exception:
        return None


def cover_crop(img: Image.Image, w: int, h: int) -> Image.Image:
    img = img.convert("RGB")
    scale = max(w / img.width, h / img.height)
    nw, nh = int(img.width * scale), int(img.height * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - w) // 2
    top = (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def darken(img: Image.Image, factor: float = 0.55) -> Image.Image:
    # multiply toward black for text legibility
    black = Image.new("RGB", img.size, (8, 14, 12))
    return Image.blend(img, black, 1.0 - factor)


def composite_banner(mood_path: Path, out: Path, w: int, h: int) -> None:
    base = cover_crop(Image.open(mood_path), w, h)
    base = darken(base, 0.48)
    # left gradient for text
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for x in range(0, int(w * 0.62)):
        alpha = int(200 * (1 - x / (w * 0.62)))
        d.line([(x, 0), (x, h)], fill=(10, 18, 14, alpha))
    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(base)

    # small logo mark from imagine icon
    icon = Image.open(IMAGINE / "icon-source.jpg").convert("RGBA")
    icon = cover_crop(icon, 72, 72).convert("RGBA")
    # round mask
    mask = Image.new("L", (72, 72), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 71, 71], radius=16, fill=255)
    base.paste(icon, (56, 48), mask)

    f_brand = load("bold", 52)
    f_tag = load("regular", 26)
    f_stat = load("bold", 110)
    f_label = load("regular", 24)
    f_foot = load("mono", 20)
    f_small = load("regular", 18)

    WHITE = (238, 244, 239)
    MUTED = (180, 196, 186)
    MINT = (111, 218, 166)
    WARN = (237, 204, 122)
    DIM = (140, 155, 146)

    d.text((148, 58), "CrewScore", font=f_brand, fill=WHITE)
    d.text((56, 140), "Find the safety rules your AI agent prompt forgot.", font=f_tag, fill=MUTED)

    count = CONCEPT_COUNT
    d.text((56, 210), str(count), font=f_stat, fill=MINT)
    d.text((56 + 170, 260), "public controls", font=f_label, fill=MUTED)
    d.text((56, 340), "injection · human approval · cost · stop · and more", font=f_label, fill=DIM)
    d.text((56, 378), "Coverage of written controls — not a safety grade.", font=f_label, fill=MUTED)

    med = median()
    # right glass panel
    px0, py0, px1, py1 = w - 360, 180, w - 56, h - 100
    panel = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle([px0, py0, px1, py1], radius=18, fill=(20, 32, 26, 200), outline=(111, 218, 166, 90), width=2)
    base = Image.alpha_composite(base.convert("RGBA"), panel).convert("RGB")
    d = ImageDraw.Draw(base)
    if med is not None:
        d.text((px0 + 28, py0 + 28), "Production median", font=f_small, fill=DIM)
        d.text((px0 + 28, py0 + 58), f"{med}/100", font=load("bold", 52), fill=WARN)
        d.text((px0 + 28, py0 + 130), "among 83 production", font=f_small, fill=MUTED)
        d.text((px0 + 28, py0 + 156), "agent prompts (356 total)", font=f_small, fill=MUTED)
        d.text((px0 + 28, py0 + 200), "Not a quality ranking.", font=f_small, fill=DIM)

    d.line([(56, h - 70), (w - 56, h - 70)], fill=(64, 81, 71), width=1)
    d.text((56, h - 52), "crewscore.ai", font=f_foot, fill=DIM)
    d.text((240, h - 52), "pip install crewscore", font=f_foot, fill=DIM)
    d.text((520, h - 52), "offline · no API key · local browser", font=f_foot, fill=DIM)

    out.parent.mkdir(parents=True, exist_ok=True)
    base.save(out, "PNG", optimize=True)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


def process_icon() -> None:
    src = Image.open(IMAGINE / "icon-source.jpg").convert("RGB")
    # center-crop to square if needed
    s = min(src.width, src.height)
    left = (src.width - s) // 2
    top = (src.height - s) // 2
    src = src.crop((left, top, left + s, top + s))
    for size, path in ((512, OUT_512), (180, OUT_APPLE)):
        im = src.resize((size, size), Image.Resampling.LANCZOS)
        # slight contrast
        im = ImageEnhance.Contrast(im).enhance(1.05)
        im.save(path, "PNG", optimize=True)
        print(f"wrote {path}")
    # favicon ico
    sizes = [16, 32, 48]
    imgs = [src.resize((s, s), Image.Resampling.LANCZOS) for s in sizes]
    ico = ROOT / "favicon.ico"
    imgs[0].save(ico, format="ICO", sizes=[(i.width, i.height) for i in imgs], append_images=imgs[1:])
    print(f"wrote {ico}")


def hero_full() -> None:
    mood = Image.open(IMAGINE / "og-mood-source.jpg")
    hero = cover_crop(mood, 1600, 900)
    OUT_HERO.parent.mkdir(parents=True, exist_ok=True)
    hero.save(OUT_HERO, "PNG", optimize=True)
    print(f"wrote {OUT_HERO}")


def main():
    composite_banner(IMAGINE / "og-mood-source.jpg", OUT_SOCIAL, 1200, 630)
    composite_banner(IMAGINE / "github-mood-source.jpg", OUT_BANNER, 1280, 640)
    process_icon()
    hero_full()
    print("done controls=", CONCEPT_COUNT, "median=", median())


if __name__ == "__main__":
    main()
