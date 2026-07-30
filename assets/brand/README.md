# CrewScore brand assets

## Mark concept

**Coverage bars** — mint fills for written controls, gold outline for the missing
gap. Not a generic shield or lock.

## Files

| File | Origin | Use |
| --- | --- | --- |
| `logo-mark.svg` | Vector (code) | Site header, small UI |
| `logo-horizontal.svg` | Vector (code) | Docs / light marketing |
| `imagine/icon-source.jpg` | **Grok Imagine** | Master icon art |
| `imagine/og-mood-source.jpg` | **Grok Imagine** | OG mood background |
| `imagine/github-mood-source.jpg` | **Grok Imagine** | README mood background |
| `imagine/lockup-source.jpg` | **Grok Imagine** | Horizontal lockup ref |
| `icon-512.png` / `apple-touch-icon.png` | Imagine → resize | App / touch icons |
| `hero-imagine.png` | Imagine crop | Marketing hero plate |
| `favicon.svg` | Vector | Sharp tab icon |
| `favicon.ico` | Imagine → multi-size | Legacy favicon |

## Social / GitHub cards (exact numbers)

Imagine art alone cannot guarantee correct stats. Raster cards are **composited**:

1. Imagine mood plate (`imagine/*-source.jpg`)
2. Exact overlay from catalog + `docs/validation-corpus.json`

```bash
# Prefer Imagine composite (when imagine/ sources exist)
py scripts/compose_imagine_brand.py

# Flat programmatic fallback (no Imagine)
py scripts/make_social_card.py

# Corpus shock card (SVG)
py scripts/generate_corpus_card.py
```

Writes: `docs/social-card.png`, `docs/github-banner.png`, icons, `favicon.ico`.

## Palette

| Token | Hex |
| --- | --- |
| Forest | `#0B4F33` |
| Mint | `#6FDAA6` |
| Warn / gap | `#EDCC7A` |
| Ink | `#0E1612` |
