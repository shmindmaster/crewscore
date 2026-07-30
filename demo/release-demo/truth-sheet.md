# Release demo truth sheet

## Persona and environment

- Persona: Mira, support lead for the fictional Northstar Clinic.
- Environment: a clean local CrewScore static-server instance in a fresh Playwright browser context.
- Data: `assets/demo-fixture.js` only. It contains no customer, patient, account, credential, or financial data.
- Timezone and locale: `America/Chicago`, `en-US`.

## Expected workflow values

| Step | Expected visible value | Source |
| --- | --- | --- |
| Initial scan | `8 of 23 written guardrails found` | `assets/demo-fixture.js` and generated `score-engine.js` |
| Initial gaps | Human approval, tamper-evident record, redaction of personal data | `assets/demo-fixture.js` `expected.missing` |
| Selected wording | `A human must approve.` | `CONTROL_FIX_TEMPLATES[human_gate.approval_required]` |
| After apply | `9 of 23 written guardrails found` and `14 controls may be missing` | Real in-browser rescan in `assets/site.js` |
| Share boundary | Ruleset, artifact profile, and found/missing control IDs only | `assets/site.js` `sharePayload` |

## Demonstrated claims

The validated claims are in `product-claims.json`. The video never says that the prompt is safe, compliant, certified, or enforced at runtime.
