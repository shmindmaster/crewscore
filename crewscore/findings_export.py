"""Serialization gate between scoring and every output that leaves the machine.

`analyze_with_findings` keeps computing the matched substring: the score is a
function of the same matches, and `crewscore test --explain` prints that text
to the local terminal on request. What must not happen by default is the
substring being copied into an artifact other people read — a `--json` payload
echoed into a build log, a job summary, a sticky PR comment, an HTML report
uploaded as a CI artifact.

A match substring is prompt text. The prompt is the artifact being scanned, not
evidence about it, so `public_findings()` drops `snippet` unless the caller
explicitly opts in with `--include-snippets`.

Scoring is untouched by this module. It only decides what the finding *looks
like* once it is serialized.
"""

from __future__ import annotations

from typing import Any

__all__ = ["finding_detail", "public_findings"]

SNIPPET_KEY = "snippet"


def public_findings(
    findings: list[dict[str, Any]] | None,
    *,
    include_snippets: bool = False,
) -> list[dict[str, Any]]:
    """Copy findings for output, dropping the matched prompt substring.

    The key is omitted rather than emitted as null: a consumer reading
    `finding["snippet"]` has to fail loudly, and a payload that says
    `"snippet": null` for every row invites the reading "nothing matched",
    which is the opposite of what a matched finding means.
    """
    if not findings:
        return []
    rows: list[dict[str, Any]] = []
    for finding in findings:
        row = {key: value for key, value in finding.items() if key != SNIPPET_KEY}
        if include_snippets and finding.get(SNIPPET_KEY) is not None:
            row[SNIPPET_KEY] = finding[SNIPPET_KEY]
        rows.append(row)
    return rows


def finding_detail(finding: dict[str, Any]) -> str:
    """Detail line for one finding, degrading to the control label.

    Downstream renderers (summary, PR comment, HTML report) receive redacted
    findings by default, so the snippet is absent and this returns
    `pattern_or_reason` — the published control label. Rendering `None` there
    would turn every matched control into a row that says nothing.
    """
    return str(
        finding.get(SNIPPET_KEY)
        or finding.get("pattern_or_reason")
        or finding.get("concept")
        or ""
    )
