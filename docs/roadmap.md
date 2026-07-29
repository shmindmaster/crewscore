# Public roadmap

This is a prioritization record, not a promise or a safety claim. CrewScore
keeps deterministic prompt-text coverage separate from runtime enforcement.

## Available now

- Browser-local checker with 23 public controls and control-level fixes.
- Offline CLI, repository scan, reports, badges, and GitHub Action.
- Explicit control policies, prompt-free regression baselines, `init`, and
  prompt-free SARIF export.
- Browser coverage across Chromium, Firefox, WebKit, mobile, and axe checks.

## Next when evidence and maintainership support it

- Framework adapters that extract prompts without pretending to enforce runtime
  behavior.
- Approved code-scanning upload recipes and richer repository findings.
- More runnable examples and plain-language instruction walkthroughs.
- Carefully governed experimental/community rule-pack process.

## Deliberately not represented as available

- Live adversarial attacks, runtime tool enforcement, or compliance
  certification.
- Fake framework loaders or unimplemented integrations.
- Dynamic server-rendered social previews for prompt-derived content.

See [next-steps-eval.md](next-steps-eval.md) for today’s honest handoff to
Promptfoo and garak.
