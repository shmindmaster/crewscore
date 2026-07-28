# CrewScore PyPI publish checklist

Package: **`crewscore`** · Version: **`0.2.0`** (see `pyproject.toml`)  
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

## Secrets (human only — never commit)

| Env var | Value |
| --- | --- |
| `TWINE_USERNAME` | `__token__` |
| `TWINE_PASSWORD` | PyPI API token (`pypi-...`) |

Export these in the shell session that runs `twine upload`. Do **not** put them in the repo, CI secrets for this prep task, or commit messages.

```powershell
# PowerShell (session-only)
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-..."   # paste token from human; never commit
```

```bash
# bash (session-only)
export TWINE_USERNAME=__token__
export TWINE_PASSWORD='pypi-...'   # paste token from human; never commit
```

## Build + validate (no upload)

```bash
py -3.13 -m pip install build twine -q
py -3.13 -m build
py -3.13 -m twine check dist/*
```

Expected:

- Artifacts: `dist/crewscore-0.2.0.tar.gz` and `dist/crewscore-0.2.0-py3-none-any.whl`
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
pip install crewscore==0.2.0
crewscore --version
# expect: 0.2.0 (or the published version string)

crewscore test --prompt "You are a helpful assistant."
```

### Tag (only after successful PyPI publish)

```bash
git tag -a v0.2.0 -m "crewscore 0.2.0"
# push tag only when human approves: git push origin v0.2.0
```

### Floating GitHub Action tag `v1` (for `uses: shmindmaster/crewscore@v1`)

Consumers pin the composite action with a **major floating tag** `v1`, not only the
immutable version tag. After a successful release (PyPI live + `v0.2.0` tag pushed),
create or move `v1` to the same commit as the release:

```bash
# First release that introduces the action major line:
git tag -a v1 -m "CrewScore Action v1 (tracks 0.2.x)"

# Later 0.2.x / 0.3.x patches that stay on Action major 1 — move the floating tag:
git tag -d v1                    # local only, if v1 already exists
git tag -a v1 -m "CrewScore Action v1 → v0.2.0"
# Force-update remote floating tag only when human approves:
# git push origin refs/tags/v1 --force
```

- `v0.2.0` (and future `vX.Y.Z`) stay **immutable** release tags.
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
- [ ] (After upload) git tag `v0.2.0` if matching this version
