"""Control-policy and regression-baseline helpers.

Policies deliberately consume the public *control* catalog, rather than the
numeric score.  That lets a team require a human approval or safe-stop rule
without turning an average coverage number into a safety bar.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from crewscore.scorers.structural_analysis import CONCEPTS


BASELINE_FORMAT = "crewscore-baseline@1"


class PolicyError(ValueError):
    """A policy or baseline is malformed or cannot be used safely."""


@dataclass(frozen=True)
class PolicySettings:
    """Resolved policy input, independent of a CLI or Action transport."""

    required_controls: tuple[str, ...] = ()
    forbidden_missing_controls: tuple[str, ...] = ()
    baseline_path: Path | None = None
    fail_on_regression: bool = False
    config_path: Path | None = None

    @property
    def enabled(self) -> bool:
        return bool(
            self.required_controls
            or self.forbidden_missing_controls
            or self.baseline_path
            or self.fail_on_regression
        )


def control_catalog() -> dict[str, tuple[str, ...]]:
    """Return the public dimension -> control-key catalog in stable order."""
    return {
        dimension: tuple(concept.key for concept in concepts)
        for dimension, concepts in CONCEPTS.items()
    }


def all_controls() -> tuple[str, ...]:
    return tuple(control for controls in control_catalog().values() for control in controls)


def _tokens(values: tuple[str, ...] | list[str] | None) -> list[str]:
    tokens: list[str] = []
    for value in values or []:
        if not isinstance(value, str):
            raise PolicyError("control names must be strings")
        tokens.extend(token.strip() for token in value.split(",") if token.strip())
    return tokens


def expand_control_selectors(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    """Expand dimension selectors and validate individual control IDs.

    ``--require human_gate`` means all published human-gate controls.  A
    control ID such as ``human_gate.approval_required`` remains precise.
    """
    catalog = control_catalog()
    known = set(all_controls())
    expanded: list[str] = []
    for selector in _tokens(values):
        if selector in catalog:
            expanded.extend(catalog[selector])
        elif selector in known:
            expanded.append(selector)
        else:
            choices = ", ".join([*catalog, *sorted(known)])
            raise PolicyError(
                f"unknown control selector '{selector}'. Use a dimension or published "
                f"control ID: {choices}"
            )
    return tuple(dict.fromkeys(expanded))


def _read_config(path: Path) -> dict[str, Any]:
    """Read the deliberately small, dependency-free .crewscore.yml schema.

    This is intentionally not a general YAML loader.  The project policy is a
    handful of scalar values and block lists; accepting a narrow, documented
    subset keeps the shipped scanner dependency-light and makes unknown YAML
    constructs fail rather than being interpreted unexpectedly.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PolicyError(f"cannot read config {path}: {exc.strerror or exc}") from exc
    data: dict[str, Any] = {}
    active_list: str | None = None
    for line_number, raw_line in enumerate(raw.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.lstrip()
        if active_list and stripped.startswith("- "):
            if len(line) == len(stripped):
                raise PolicyError(
                    f"invalid list indentation in {path}:{line_number}; use two spaces before -"
                )
            item = stripped[2:].strip()
            if not item:
                raise PolicyError(f"empty list item in {path}:{line_number}")
            data[active_list].append(_unquote(item))
            continue
        active_list = None
        if line != stripped or ":" not in line:
            raise PolicyError(f"invalid config line {path}:{line_number}")
        key, value = (part.strip() for part in line.split(":", 1))
        if key in data:
            raise PolicyError(f"duplicate config key '{key}' in {path}:{line_number}")
        if key in {"required_controls", "forbid_missing"}:
            if value == "[]":
                data[key] = []
            elif value == "":
                data[key] = []
                active_list = key
            else:
                raise PolicyError(
                    f"config '{key}' in {path}:{line_number} must be [] or an indented list"
                )
        elif value:
            data[key] = _unquote(value)
        else:
            raise PolicyError(f"missing value for '{key}' in {path}:{line_number}")
    allowed = {
        "version",
        "baseline",
        "required_controls",
        "forbid_missing",
        "fail_on_regression",
    }
    unknown = set(data).difference(allowed)
    if unknown:
        raise PolicyError(f"unknown config key(s): {', '.join(sorted(unknown))}")
    if "version" in data and data["version"] not in (1, "1"):
        raise PolicyError("only .crewscore.yml version: 1 is supported")
    for key in ("required_controls", "forbid_missing"):
        if key in data and not isinstance(data[key], list):
            raise PolicyError(f"config '{key}' must be a YAML list")
    if "baseline" in data and not isinstance(data["baseline"], str):
        raise PolicyError("config 'baseline' must be a path string")
    if "fail_on_regression" in data and data["fail_on_regression"] not in ("true", "false"):
        raise PolicyError("config 'fail_on_regression' must be true or false")
    if "fail_on_regression" in data:
        data["fail_on_regression"] = data["fail_on_regression"] == "true"
    return data


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def resolve_policy(
    *,
    config: str | None,
    require: tuple[str, ...] | list[str] | None,
    forbid_missing: tuple[str, ...] | list[str] | None,
    baseline: str | None,
    fail_on_regression: bool,
    cwd: Path | None = None,
) -> PolicySettings:
    """Combine config and explicit CLI values; explicit values add to config."""
    cwd = cwd or Path.cwd()
    config_path = Path(config).resolve() if config else None
    configured = _read_config(config_path) if config_path else {}

    required = expand_control_selectors(
        [*(configured.get("required_controls") or []), *(require or [])]
    )
    forbidden = expand_control_selectors(
        [*(configured.get("forbid_missing") or []), *(forbid_missing or [])]
    )
    baseline_value = baseline if baseline is not None else configured.get("baseline")
    baseline_path = None
    if baseline_value:
        base_dir = config_path.parent if config_path else cwd
        baseline_path = (base_dir / baseline_value).resolve()
    resolved_fail = bool(fail_on_regression or configured.get("fail_on_regression", False))
    if resolved_fail and baseline_path is None:
        raise PolicyError("--fail-on-regression requires --baseline or config baseline")
    return PolicySettings(
        required_controls=required,
        forbidden_missing_controls=forbidden,
        baseline_path=baseline_path,
        fail_on_regression=resolved_fail,
        config_path=config_path,
    )


def found_controls(findings: list[dict[str, Any]]) -> set[str]:
    return {
        finding["concept"]
        for finding in findings
        if finding.get("status") == "matched" and finding.get("concept")
    }


def _load_baseline(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PolicyError(f"baseline not found: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"cannot read baseline {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("format") != BASELINE_FORMAT:
        raise PolicyError(f"baseline {path} is not a {BASELINE_FORMAT} file")
    if not isinstance(data.get("files"), dict):
        raise PolicyError(f"baseline {path} has no files mapping")
    # A control ID can survive a ruleset release while its patterns or grouping
    # change. Comparing across that boundary looks precise but is not the same
    # evidence, so force an intentional baseline review/regeneration.
    from crewscore.scoring import RULESET_ID

    if data.get("ruleset") != RULESET_ID:
        raise PolicyError(
            f"baseline ruleset {data.get('ruleset')!r} does not match current "
            f"{RULESET_ID}; review and regenerate it"
        )
    return data


def _baseline_controls(
    baseline: dict[str, Any], *, source: str, root: Path | None
) -> set[str] | None:
    candidates = [source.replace("\\", "/")]
    source_path = Path(source)
    if root is not None:
        try:
            candidates.insert(0, source_path.resolve().relative_to(root.resolve()).as_posix())
        except (OSError, ValueError):
            pass
    if source == "prompt":
        candidates.insert(0, "__prompt__")
    for candidate in candidates:
        record = baseline["files"].get(candidate)
        if record is None:
            continue
        controls = record.get("found_controls") if isinstance(record, dict) else record
        if not isinstance(controls, list) or not all(isinstance(item, str) for item in controls):
            raise PolicyError(
                f"baseline entry for {candidate} must contain a found_controls list"
            )
        return set(controls)
    return None


def evaluate_policy(
    settings: PolicySettings,
    *,
    findings: list[dict[str, Any]],
    governance_applicable: bool,
    source: str,
    root: Path | None = None,
) -> dict[str, Any]:
    """Return a content-free policy record and whether it should fail CI."""
    if not settings.enabled:
        return {"enabled": False, "failed": False}
    if not governance_applicable:
        return {
            "enabled": True,
            "applicable": False,
            "failed": False,
            "reason": "governance_controls_do_not_apply_to_config",
        }

    detected = found_controls(findings)
    must_have = set(settings.required_controls).union(settings.forbidden_missing_controls)
    missing = sorted(must_have.difference(detected))
    record: dict[str, Any] = {
        "enabled": True,
        "applicable": True,
        "required_controls": list(settings.required_controls),
        "forbidden_missing_controls": list(settings.forbidden_missing_controls),
        "missing_required_controls": missing,
        "regressed_controls": [],
        "baseline_missing_for_path": False,
        "failed": bool(missing),
    }
    if settings.baseline_path is not None:
        baseline = _load_baseline(settings.baseline_path)
        prior = _baseline_controls(baseline, source=source, root=root)
        record["baseline"] = str(settings.baseline_path)
        if prior is None:
            record["baseline_missing_for_path"] = True
        else:
            regressions = sorted(prior.difference(detected))
            record["regressed_controls"] = regressions
            if settings.fail_on_regression and regressions:
                record["failed"] = True
    return record


def baseline_payload(
    entries: list[tuple[str, str, list[dict[str, Any]]]], *, ruleset: str
) -> dict[str, Any]:
    """Create a stable, prompt-free baseline payload from scored artifacts."""
    files: dict[str, dict[str, Any]] = {}
    for path, profile, findings in entries:
        files[path.replace("\\", "/")] = {
            "profile": profile,
            "found_controls": sorted(found_controls(findings)),
        }
    return {
        "format": BASELINE_FORMAT,
        "ruleset": ruleset,
        "files": dict(sorted(files.items())),
    }
