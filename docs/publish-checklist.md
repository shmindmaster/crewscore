# CrewScore PyPI publish checklist

Package: **`crewscore`** · Version: **see `pyproject.toml`** (currently 0.2.x)  
Build backend: **hatchling** · Do **not** upload without a human-provided token.

## Prerequisites

- Python 3.11+ available (`py -3.13` recommended for the build machine)
- Clean working tree on the release branch
- `pyproject.toml` metadata verified:
  - `name = "crewscore"`
  - scripts: `crewscore` and legacy `agent-guard` → `crewscore.cli:main`
  - URLs: Homepage `https://crewscore.ai`, Repository `https://github.com/shmindmaster/crewscore`
- PyPI project name `crewscore` is free / owned by us
- Human has a PyPI API token ready (see secrets below)

## Secrets (1Password — never commit)

Canonical credential (Business & Apps vault):

| Field | Value |
| --- | --- |
| Item | **PyPI API Token — Main (Upload packages)** |
| Item ID | `thabtkjmhdpamdshpn7urq2rqa` |
| Vault ID | `d4yvwfzjsyw4x6mymqjjfcxcoe` (name contains `&`; prefer ID in `op://` refs) |
| Twine username | `__token__` (item field `username`) |
| Twine password | item field `credential` (concealed API token) |
| Scope | Entire account · Upload packages · token name “Main” |

Load into the shell only for upload, then clear:

```powershell
# PowerShell — read from 1Password (session-only; never commit)
$vault = "d4yvwfzjsyw4x6mymqjjfcxcoe"
$id = "thabtkjmhdpamdshpn7urq2rqa"
$env:TWINE_USERNAME = op read "op://$vault/$id/username"
$env:TWINE_PASSWORD = op read "op://$vault/$id/credential"
# ... twine upload ...
Remove-Item Env:TWINE_USERNAME, Env:TWINE_PASSWORD -ErrorAction SilentlyContinue
```

```bash
# bash — session-only
export TWINE_USERNAME="$(op read 'op://d4yvwfzjsyw4x6mymqjjfcxcoe/thabtkjmhdpamdshpn7urq2rqa/username')"
export TWINE_PASSWORD="$(op read 'op://d4yvwfzjsyw4x6mymqjjfcxcoe/thabtkjmhdpamdshpn7urq2rqa/credential')"
# ... twine upload ...
unset TWINE_USERNAME TWINE_PASSWORD
```

Do **not** put tokens in the repo, commit messages, CI logs, or permanent `.pypirc` unless that file is outside git and gitignored.

## Build + validate (no upload)

```bash
py -3.13 -m pip install build twine -q
py -3.13 -m build
py -3.13 -m twine check dist/*
```

Expected:

- Artifacts: `dist/crewscore-<version>.tar.gz` and `dist/crewscore-<version>-py3-none-any.whl`
- `twine check` reports **PASSED** for both

Optional hatch path (equivalent if hatch is installed):

```bash
py -3.13 -m pip install hatch twine -q
hatch build
py -3.13 -m twine check dist/*
```

## Publish (manual, credentials required)

**Stop here unless a human has approved the release and set `TWINE_USERNAME` / `TWINE_PASSWORD`.**

```bash
# TestPyPI first (recommended)
py -3.13 -m twine upload --repository testpypi dist/*

# Production PyPI (after TestPyPI smoke install)
py -3.13 -m twine upload dist/*
```

### Post-upload smoke

```bash
# clean venv recommended
pip install "crewscore==$(python -c 'import tomllib; print(tomllib.load(open(\"pyproject.toml\",\"rb\"))[\"project\"][\"version\"])')"
# or: pip install crewscore==X.Y.Z matching pyproject.toml
crewscore --version
# expect: the published version string

crewscore test --prompt "You are a helpful assistant."
```

### Tag (only after successful PyPI publish)

```bash
VERSION=$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
git tag -a "v$VERSION" -m "crewscore $VERSION"
# push tag only when human approves: git push origin "v$VERSION"
```

### Floating GitHub Action tag `v1` (for `uses: shmindmaster/crewscore@v1`)

Consumers pin the composite action with a **major floating tag** `v1`, not only the
immutable version tag. After a successful release (PyPI live + `vX.Y.Z` tag pushed),
create or move `v1` to the same commit as the release:

```bash
# First release that introduces the action major line:
git tag -a v1 -m "CrewScore Action v1 (tracks 0.2.x)"

# Later 0.2.x / 0.3.x patches that stay on Action major 1 — move the floating tag:
git tag -d v1                    # local only, if v1 already exists
git tag -a v1 -m "CrewScore Action v1 → v$VERSION"
# Force-update remote floating tag only when human approves:
# git push origin refs/tags/v1 --force
```

- `vX.Y.Z` stay **immutable** release tags.
- `v1` is a **movable major pointer** so workflows using
  `uses: shmindmaster/crewscore@v1` pick up compatible Action fixes without
  editing every consumer workflow.
- Do **not** push `v1` until the matching release commit is published and the
  human has approved the tag move.
- Breaking Action input/output changes require a new major (`v2`), not moving `v1`
  across an incompatible contract.

## Do not

- Run `twine upload` without human-supplied `TWINE_USERNAME` / `TWINE_PASSWORD`
- Commit API tokens, `.pypirc` with secrets, or env files containing `pypi-`
- Create or push a git tag before the package is live on PyPI
- Document `pip install agent-guard` as this product (unrelated third-party package)
- Push or force-move floating `v1` without human approval

## Pre-flight metadata checklist

- [ ] `pyproject.toml` version matches intended release
- [ ] README install CTA is `pip install crewscore`
- [ ] `project.scripts` has `crewscore` + legacy `agent-guard`
- [ ] `project.urls` Homepage / Repository / Issues / Documentation correct
- [ ] `twine check dist/*` PASSED
- [ ] Human approved upload + provided token
- [ ] (After upload) clean-machine install + `crewscore --version`
- [ ] (After upload) git tag `vX.Y.Z` matching `pyproject.toml`
