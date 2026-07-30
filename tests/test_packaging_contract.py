"""Every test import must be installable from `pip install -e ".[dev]"`.

The 0.5.1 release failed its CI gate because a new test imported pyyaml, which
was present on the author's machine and declared nowhere. The gate was right
and nothing published - but the failure only surfaced after the tag was
pushed, which is the most expensive moment to learn it.

A local `pytest` run cannot catch this: the module is already installed. So the
check is static, over the declared dependency set rather than the environment.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TESTS = REPO / "tests"

# Import name -> distribution name, where they differ.
IMPORT_TO_DISTRIBUTION = {"yaml": "pyyaml"}

# Modules that live in this repository rather than on an index.
FIRST_PARTY = {"crewscore", "validate_corpus", "tests", "conftest", "scripts"}


def _declared() -> set[str]:
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    specs = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        specs.extend(extra)
    return {re.split(r"[<>=!~\[]", s)[0].strip().lower() for s in specs}


def _imports(path: Path) -> set[str]:
    src = path.read_text(encoding="utf-8")
    return set(re.findall(r"^\s*(?:import|from)\s+([A-Za-z_]\w*)", src, re.M))


def test_every_test_import_is_a_declared_dependency():
    declared = _declared()
    stdlib = set(sys.stdlib_module_names)
    undeclared: dict[str, list[str]] = {}
    for path in sorted(TESTS.glob("*.py")):
        for module in _imports(path):
            if module in stdlib or module in FIRST_PARTY:
                continue
            dist = IMPORT_TO_DISTRIBUTION.get(module, module)
            if dist.lower() not in declared:
                undeclared.setdefault(dist, []).append(path.name)
    assert not undeclared, (
        "these are imported by tests but not declared in pyproject.toml, so a "
        f"clean CI checkout cannot install them: {undeclared}"
    )


def test_the_shipped_package_stays_dependency_light():
    """Test tooling may grow; the runtime install must not follow it.

    "Offline, no API key" is a claim about what a user installs, and every
    runtime dependency is surface area behind that claim.
    """
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    runtime = {
        re.split(r"[<>=!~\[]", s)[0].strip().lower()
        for s in data["project"].get("dependencies", [])
    }
    assert runtime <= {"click", "rich"}, (
        f"new runtime dependency: {sorted(runtime - {'click', 'rich'})}"
    )
    assert "pyyaml" not in runtime, "pyyaml is a test-only dependency"


def test_dev_extra_exists_and_carries_pytest():
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    dev = data["project"]["optional-dependencies"]["dev"]
    assert any(s.lower().startswith("pytest") for s in dev), dev
