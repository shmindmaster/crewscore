# Security policy

CrewScore is an offline static-analysis tool. Please report suspected security
issues privately rather than opening a public issue, especially if they could
expose prompt text, source URLs, analytics data, Action consumers, or a supply
chain dependency.

The project is created and maintained by **Sarosh Hussain**. **Pendoah** is the
company operating context; the repository's code and security process define
the technical claims and safeguards.

## Report privately

Use GitHub's [private vulnerability reporting flow](https://github.com/shmindmaster/crewscore/security/advisories/new).
If GitHub is unavailable to you, email [sarosh@pendoah.ai](mailto:sarosh@pendoah.ai)
with `CrewScore security report` in the subject line. Do not include secrets,
customer prompts, or exploit payloads in a public GitHub issue.

Include the affected version or commit, a minimal synthetic reproduction,
impact, and any suggested mitigation. We will acknowledge a report, assess the
scope, and coordinate a fix and disclosure timeline with the reporter.

## Scope

Relevant reports include the Python package, GitHub Action, static website,
generated browser engine, build/release automation, and published
dependencies. A false positive or missing written control is normally a
scoring-quality issue; use the false-positive/false-negative templates unless
it creates a concrete security exposure.
