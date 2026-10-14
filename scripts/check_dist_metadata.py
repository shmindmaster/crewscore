#!/usr/bin/env python3
"""Reject non-portable links in built package long descriptions.

PyPI renders the long description outside the repository, so repository-
relative Markdown and HTML targets become broken `/project/...` URLs. Inspect
the actual wheel METADATA and sdist PKG-INFO rather than trusting README source.
"""

from __future__ import annotations

import argparse
import re
import sys
import tarfile
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import urlsplit

MARKDOWN_LINK_RE = re.compile(
    r"(?P<image>!)?\[[^\]]*\]\(\s*(?:<(?P<angle>[^>]+)>|(?P<plain>[^\s)]+))",
    re.MULTILINE,
)
REFERENCE_LINK_RE = re.compile(
    r"^\s*\[[^\]]+\]:\s*(?:<(?P<angle>[^>]+)>|(?P<plain>\S+))",
    re.MULTILINE,
)
HTML_TARGET_RE = re.compile(
    r"<[^>]+\b(?P<attribute>href|src)\s*=\s*(?:"
    r"(?P<quote>['\"])(?P<quoted>.*?)(?P=quote)|(?P<unquoted>[^\s>]+)"
    r")[^>]*>",
    re.IGNORECASE | re.DOTALL,
)
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
ALLOWED_SCHEMES = {"data", "http", "https", "mailto"}


def _without_fenced_code(text: str) -> str:
    rendered: list[str] = []
    fence: str | None = None
    for line in text.splitlines(keepends=True):
        match = FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker[0]
            elif marker[0] == fence:
                fence = None
            rendered.append("\n" if line.endswith("\n") else "")
        elif fence is None:
            rendered.append(line)
        else:
            rendered.append("\n" if line.endswith("\n") else "")
    return "".join(rendered)


def _is_portable_target(target: str) -> bool:
    target = target.strip()
    if not target:
        return False
    if target.startswith("#"):
        return True
    parsed = urlsplit(target)
    scheme = parsed.scheme.lower()
    if scheme in {"http", "https"}:
        return bool(parsed.netloc)
    return scheme in ALLOWED_SCHEMES


def find_nonportable_targets(description: str) -> list[tuple[str, str]]:
    """Return relative or unsupported rendered link targets in stable order."""
    text = _without_fenced_code(description)
    violations: list[tuple[str, str]] = []

    for match in MARKDOWN_LINK_RE.finditer(text):
        target = match.group("angle") or match.group("plain") or ""
        if not _is_portable_target(target):
            kind = "markdown image" if match.group("image") else "markdown link"
            violations.append((kind, target))

    for match in REFERENCE_LINK_RE.finditer(text):
        target = match.group("angle") or match.group("plain") or ""
        if not _is_portable_target(target):
            violations.append(("markdown reference", target))

    for match in HTML_TARGET_RE.finditer(text):
        target = match.group("quoted") or match.group("unquoted") or ""
        if not _is_portable_target(target):
            violations.append((f"html {match.group('attribute').lower()}", target))

    return violations


def _long_description(metadata: bytes) -> str:
    message = BytesParser(policy=policy.default).parsebytes(metadata)
    payload = message.get_payload()
    if not isinstance(payload, str):
        raise ValueError("package metadata long description is not text")
    return payload


def _wheel_metadata(path: Path) -> tuple[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(members) != 1:
            raise ValueError(f"{path.name}: expected one wheel METADATA, found {len(members)}")
        return members[0], archive.read(members[0])


def _sdist_metadata(path: Path) -> tuple[str, bytes]:
    with tarfile.open(path, mode="r:*") as archive:
        members = [
            member
            for member in archive.getmembers()
            if member.isfile() and member.name.endswith("/PKG-INFO")
        ]
        if len(members) != 1:
            raise ValueError(f"{path.name}: expected one sdist PKG-INFO, found {len(members)}")
        extracted = archive.extractfile(members[0])
        if extracted is None:
            raise ValueError(f"{path.name}: could not read {members[0].name}")
        return members[0].name, extracted.read()


def _artifacts(paths: list[Path]) -> list[Path]:
    artifacts: list[Path] = []
    for path in paths:
        if path.is_dir():
            artifacts.extend(sorted(path.glob("*.whl")))
            artifacts.extend(sorted(path.glob("*.tar.gz")))
        else:
            artifacts.append(path)
    return artifacts


def check_artifacts(paths: list[Path]) -> list[str]:
    artifacts = _artifacts(paths)
    if not artifacts:
        raise ValueError("no wheel or sdist artifacts found")

    kinds = {"wheel" if path.suffix == ".whl" else "sdist" for path in artifacts}
    if kinds != {"wheel", "sdist"}:
        raise ValueError("expected at least one wheel and one sdist")

    violations: list[str] = []
    for path in artifacts:
        if path.suffix == ".whl":
            member, metadata = _wheel_metadata(path)
        elif path.name.endswith(".tar.gz"):
            member, metadata = _sdist_metadata(path)
        else:
            raise ValueError(f"unsupported distribution artifact: {path}")

        targets = find_nonportable_targets(_long_description(metadata))
        print(f"checked={_console_safe(path.name)}:{_console_safe(member)}")
        violations.extend(
            f"{path.name}:{member}: {kind}: {target!r}" for kind, target in targets
        )
    return violations


def _console_safe(value: object) -> str:
    """Render dynamic diagnostics without depending on the console encoding."""
    return str(value).encode("ascii", "backslashreplace").decode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Distribution files or directories")
    args = parser.parse_args()

    try:
        violations = check_artifacts(args.paths)
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {_console_safe(exc)}", file=sys.stderr)
        return 2

    if violations:
        print("ERROR: package long description contains non-portable links:", file=sys.stderr)
        for violation in violations:
            print(f"- {_console_safe(violation)}", file=sys.stderr)
        return 1

    print("long_description_links=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
