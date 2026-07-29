# CrewScore real-product release demo

This package produces a short narrated video from the actual local CrewScore static application. It is not a mocked screen: the browser fills the public fictional fixture, submits it to the generated browser engine, selects the real approval-control suggestion, applies it, and verifies the live 20-to-21 control rescan.

The capture intentionally uses a fresh Playwright context as the isolated demo workspace. It clears browser storage, pins locale/timezone, serves only the checked-out local application, and uses the fictional `assets/demo-fixture.js` data. Raw captures and renders are written under the ignored `_production/` directory.

## Reproduce

```powershell
npm run demo:narration
npm run demo:capture
npm run demo:render
```

Outputs include the clean and burned-caption masters, transcript/caption files, capture manifest, truth sheet, claim ledger, checksums, and a human-review template. The local Windows system voice is used so no external TTS request, credential, or billing is involved.

Run `npm run test:web` before capture. The product-experience handoff is generated in `_product-experience/` for the exact source revision and must validate before master capture. A named human must still complete the evidence manifest before any external upload or public-site replacement.
