# CrewScore brand assets

## Mark

The logo is **coverage bars** — filled segments of written controls, with one
dashed gap for what is still missing. It is not a generic shield or lock.

| File | Use |
| --- | --- |
| `logo-mark.svg` | Site header, README, app icon base |
| `logo-horizontal.svg` | Wordmark + mark |
| `apple-touch-icon.png` | iOS / home screen (180) |
| `icon-512.png` | High-res icon |

## Palette

| Token | Hex | Role |
| --- | --- | --- |
| Forest | `#0B4F33` | Mark tile, accent strong |
| Mint | `#6FDAA6` | Covered controls, highlights |
| Mint soft | `#A3EDC4` | Secondary fill |
| Warn | `#EDCC7A` | Missing control / hero gap |
| Ink | `#0E1612` | Dark surfaces |

Aligned with `assets/site.css`.

## Regenerate raster assets

```bash
py scripts/make_social_card.py      # social-card, github-banner, icons, favicon.ico
py scripts/generate_corpus_card.py  # dist-pack corpus shock card
```

Do not hand-edit `docs/social-card.png` shock numbers — they come from the
rule catalog and `docs/validation-corpus.json`.
