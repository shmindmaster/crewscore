"""Containment rules shared by every CrewScore discovery walk.

`scan` and `extract_inline` both walk a caller-selected root, and neither may
read outside it. A link pointing out of the tree would pull in files the caller
never selected, and a directory link pointing at its own ancestor would hang the
walk.

The policy is fail closed: links are never followed. A symlinked or junctioned
directory is not descended at all, which makes cycles structurally impossible
rather than something the walk has to notice, and a symlinked file is never
opened. Every refusal is reported, so "skipped as unsafe" can never be read as
"there was nothing there". There is deliberately no flag to opt back in.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import AbstractSet

DESCEND = "descend"
READ = "read"
SKIP = "skip"

REASON_SYMLINKED_DIR = "symlinked_directory_not_followed"
REASON_SYMLINKED_FILE = "symlinked_file_not_followed"
REASON_BROKEN_LINK = "broken_link_skipped"
REASON_UNRESOLVABLE_LINK = "unresolvable_link_skipped"
REASON_OUTSIDE_ROOT = "resolves_outside_scan_root"

# Junctions and mount points do not carry S_IFLNK, but they escape a scan root
# exactly like a symlink does.
_FILE_ATTRIBUTE_REPARSE_POINT = 0x0400

# Console output stays cp1252-encodable, so every string here is ASCII.
SKIP_REASON_TEXT = {
    REASON_SYMLINKED_DIR: "symlinked directory, not followed",
    REASON_SYMLINKED_FILE: "symlinked file, not followed",
    REASON_BROKEN_LINK: "broken link, skipped",
    REASON_UNRESOLVABLE_LINK: "link could not be resolved, skipped",
    REASON_OUTSIDE_ROOT: "resolves outside the scan root, skipped",
}


@dataclass(frozen=True)
class SkippedPath:
    """One path discovery refused to open because it could leave the root."""

    path: Path
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {"path": str(self.path), "reason": self.reason}


def resolve_root(root: Path | str) -> Path:
    """Canonicalize the caller-selected root once; the result is the boundary.

    The root may itself be reached through a link - the caller asked for it by
    name - so it is resolved rather than rejected.
    """
    return Path(root).resolve()


def is_within(candidate: Path | str, root_resolved: Path) -> bool:
    """True only when candidate resolves to root_resolved or something under it.

    Unresolvable paths are treated as outside the root: nothing that cannot be
    pinned down gets opened.
    """
    try:
        return Path(candidate).resolve().is_relative_to(root_resolved)
    except (OSError, RuntimeError, ValueError):
        return False


def is_link(path: Path | str) -> bool:
    """True for symlinks and for Windows junctions / other reparse points."""
    try:
        info = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    return bool(getattr(info, "st_file_attributes", 0) & _FILE_ATTRIBUTE_REPARSE_POINT)


def _resolve(path: Path) -> Path | None:
    try:
        return Path(path).resolve()
    except (OSError, RuntimeError):
        return None


def classify_entry(
    entry: Path,
    root_resolved: Path,
    *,
    ignore_names: AbstractSet[str] | None = None,
) -> tuple[str, str | None]:
    """Decide what a discovery walk may do with one directory entry.

    Returns `(DESCEND | READ | SKIP, reason)`; `reason` is set only for SKIP.

    `ignore_names` is consulted before containment, and only for directories and
    links: those trees are excluded by rule rather than by containment, and a
    linked `node_modules` is not descended either way, so reporting it as an
    escape would bury the real signal in dependency noise.
    """
    linked = is_link(entry)
    resolved = _resolve(entry)
    if resolved is None:
        return SKIP, REASON_UNRESOLVABLE_LINK
    if ignore_names is not None and entry.name in ignore_names:
        if linked or not resolved.is_file():
            return SKIP, None
    if linked and not resolved.exists():
        return SKIP, REASON_BROKEN_LINK
    if not resolved.is_relative_to(root_resolved):
        return SKIP, REASON_OUTSIDE_ROOT
    if resolved.is_dir():
        if linked:
            return SKIP, REASON_SYMLINKED_DIR
        return DESCEND, None
    if resolved.is_file():
        if linked:
            return SKIP, REASON_SYMLINKED_FILE
        return READ, None
    return SKIP, None
