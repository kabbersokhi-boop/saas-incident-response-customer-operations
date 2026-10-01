# Portfolio evidence index

Six retained images support the [root portfolio page](../../../README.md). Every image is a real application/editor screenshot. None is an AI-generated image, reconstructed UI, or rendered workflow diagram. The two Mermaid diagrams in the root README are authored explanatory diagrams, not application evidence.

## Capture provenance

| File | Source and type | What it proves | Current / historical | Privacy |
| --- | --- | --- | --- | --- |
| [relaycart-final-recovery.png](relaycart-final-recovery.png) | Real RelayCart browser screenshot, `http://127.0.0.1:8001`; native clip of technical and customer panels | Three signals, consumed approval, version-bound rollback, four passing checks; 18 affected, 1 confirmed, 16 pending, 1 follow-up; Acme/Ocean/Green Dental examples | Fresh launch capture, 2026-10-01; `INC-F25410A828C8` | Only seeded synthetic names and incident evidence; no browser chrome, credentials, or personal contact fields |
| [n8n-technical-response.png](n8n-technical-response.png) | Real n8n editor, IR 02 — Evidence and NIM Investigation; workflow `OvrKKVaPxERgQNnr` | Persisted signals + current snapshot → bounded request → real NIM / controlled failure branch → schema/evidence validation → deterministic policy | Fresh launch capture, 2026-10-01; installed 14-node graph matches export | Canvas only; no execution payload or credential editor. IR 02 chosen for clearer framing than the larger IR 04 graph |
| [n8n-ghl-impact-sync.png](n8n-ghl-impact-sync.png) | Real n8n editor, GHL 01 — Customer Impact Sync; workflow `lhpMBpbBH3j4BDjm` | PostgreSQL enqueue/claim, per-customer loop, lookup/create/update, remote-ID persistence, association, success/retry | Fresh launch capture, 2026-10-01; installed 24-node graph matches export | Wide canvas preserves the complete graph; open full resolution for node labels; no secrets or unrelated workflows |
| [n8n-ghl-feedback.png](n8n-ghl-feedback.png) | Real n8n editor, GHL 02 — Customer Recovery Feedback; workflow `tjUprwydaLuekcMg` | Outcome marker → conversation → fresh matching reply → outcome branch → task handling → persistence → transient tag cleanup | Fresh launch capture, 2026-10-01; installed 28-node graph matches export | Canvas only, no inbox, customer messages, execution bodies, or credentials; open full resolution |
| [ghl-service-cases.png](ghl-service-cases.png) | Real HighLevel Service Case list; unchanged copy of [Phase 3 capture](../phase3-ghl-service-case-list.png) | Native Custom Object, RelayCart Demo location, 18 synthetic cases, technical/customer columns | Historical Phase 3: `INC-57C615E767C3`; retained in commit `9e1fd37`. Not a capture of the current incident | Synthetic case list only; no contact emails, phones, unrelated records, credentials, or storage. Some columns are truncated by the original UI |
| [ghl-conversation-ai-workflow.png](ghl-conversation-ai-workflow.png) | Real native HighLevel workflow; unchanged copy of [Phase 3 capture](../phase3-ghl-workflow-ai-builder.png) | RelayCart — Customer Recovery Confirmation; Conversation AI action, checkout-working, still-broken, timeout and fallback branches; AI panel context | Historical Phase 3, retained in commit `9e1fd37`; current publication checked separately through the API | Workflow canvas only, no inbox/credentials. Does not show the original builder prompt or generation transcript |

The historical assets were deliberately retained because the current HighLevel UI failed to render in the available authenticated browser profiles, including a headed attempt. No workflow was rebuilt or modified to create a screenshot. Historical UI evidence demonstrates structure, while the [launch audit](launch-audit.md) proves current state through live API reads.

## Reproduction

The fresh captures use an existing private Chromium profile with Playwright. The script opens installed workflows, changes only viewport/zoom framing, and clips the actual dashboard. It never executes workflows, modifies data, or exports browser storage.

```bash
python scripts/capture-portfolio.py --profile /path/to/private/profile --chromium /path/to/chromium
```

Requires Playwright in the selected Python environment, Chromium, local RelayCart/n8n, and an existing n8n login. Browser profiles are private and must never be committed. Review outputs visually before publishing; no script can certify privacy from pixels alone.

The fresh PNGs were visually reviewed at capture and publication. Retained GHL files were also reviewed and copied byte-for-byte, preserving their evidence provenance. No optional inbox screenshots were retained. Older engineering evidence remains in [the parent index](../README.md).
