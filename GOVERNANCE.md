# Governance

CrewScore is an MIT-licensed public project maintained by Sarosh Hussain. Technical direction is currently maintainer-led. The project does not claim a broader maintainer council, customers, or adoption that has not been independently verified.

## Decisions

- Bugs, scoring proposals, and documentation changes start in a public GitHub issue or pull request unless they contain an undisclosed vulnerability or private prompt data.
- Scoring decisions follow the published rule catalog and the process in `docs/scoring-and-controls.md`.
- A new or changed control must state its provenance, include synthetic regression fixtures, regenerate the browser engine, and update validation and changelog material.
- Material decisions are recorded in the issue or pull request that implements them. A roadmap item is not current behavior until it is merged, released, and documented as such.

## Contributions and review

Contributors follow [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md). Pull requests must explain the claim or behavior being changed, the evidence behind it, validation performed, and any privacy or compatibility impact.

The maintainer may decline changes that turn coverage into a safety ranking, score coding-agent configuration as governance, expose prompt snippets by default, add an LLM dependency to the core path, or claim runtime behavior from static text matches.

## Security and privacy

Undisclosed vulnerabilities use [SECURITY.md](SECURITY.md). Customer prompts, credentials, private source URLs, and unredacted matched snippets do not belong in public issues, fixtures, or build artifacts.

## Funding

Funding may support corpus work, independent review, rule validation, framework mapping, maintenance, and public integrations, but does not buy a favorable conclusion or private control of the ruleset. Material grants, restrictions, overlapping funded work, and delivery updates will be disclosed in the relevant public issue or project update. Requested, awarded, received, and spent funds remain separate states.

## Evolution

If independent contributors begin sustaining the ruleset or integrations, governance can expand through a public proposal that names responsibilities, review authority, conflicts of interest, and removal criteria. Until then, this document states the current single-maintainer structure.
