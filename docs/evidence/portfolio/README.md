# Portfolio evidence index

The [root portfolio page](../../../README.md) now leads with the **2026-10-03 recorded demo**, `INC-7E39998CA856`. The [walkthrough](../../portfolio-demo.md) explains the exact sequence and platform boundaries. Current images are frames from the reviewed video; older captures remain available below as historical engineering evidence.

No image is an AI-generated or reconstructed UI. The Mermaid diagrams in the root README explain the architecture; they are not application evidence.

## Current recorded demo

| Asset | What it shows |
| --- | --- |
| [Complete MP4](demo/RelayCart-End-to-End-Demo.mp4) · [Preview GIF](demo/demo-preview.gif) · [Poster](demo/demo-poster.png) | One edited 3:25 story, including all six n8n paths and all three published native GHL workflows |
| [Healthy checkout](demo/01-healthy-checkout.png) · [Failed deployment](demo/02-failed-deployment.png) | Healthy order creation followed by deployment completion with business failure |
| [Investigation execution](demo/03-investigation-success.png) · [Exact approval](demo/04-human-approval.png) | Actual schema rejection, deterministic policy and human authorization boundary |
| [Four recovery checks](demo/05-verified-recovery.png) | Final release, health, checkout creation and order read-back all pass |
| [Impact-sync execution](demo/06-impact-sync-success.png) · [18 live cases](demo/07-live-service-cases.png) | Durable reconciliation into GHL, filtered to the recorded incident |
| [Native intake](demo/08-ghl-service-case-intake.png) · [Native recovery](demo/09-ghl-technical-recovery.png) | Created-case note and recovered-case handoff through actual published GHL builders |
| [Native confirmation](demo/10-ghl-customer-confirmation.png) · [Actual question](demo/11-ghl-conversation-ai-question.png) | Native Conversation AI, LiveChat configuration and explicit outcome branches |
| [Feedback execution](demo/12-feedback-success.png) | Actual successful positive/negative reply handling and task reconciliation |
| [Acme confirmed](demo/13-acme-confirmed.png) · [Ocean follow-up](demo/14-ocean-follow-up.png) · [One scoped task](demo/15-follow-up-task.png) | Technical/customer status separation and human support ownership |
| [Final dashboard](demo/16-customer-outcomes.png) · [Scoped verification](demo/verification.json) | 18 affected, 1 confirmed, 1 follow-up, 16 awaiting; unaffected control; older records preserved |

**Source:** authenticated browser-page capture at 1600×900, edited into a 1920×1080 MP4 at 30 fps. PNGs are full-output video frames; the editorial headings and scope captions are part of the video, not native application UI. The GIF is a short selection of reviewed chapters, not the full demo. No workflow or field was modified to improve its screenshot.

**Scope:** SaaS releases and orders are local synthetic operations; n8n executions and GHL API records are real. Fresh synthetic replies use the native LiveChat API test transport. The actual NIM response was rejected for an invalid schema, with no approval bypass. The successful investigation execution proves orchestration completion, not validated AI output.

**Verification:** read-only database and live GHL checks confirmed the exact incident, four passing checks, consumed approval, 18 current cases, 16/1/1 customer outcomes, Contact associations and one current-incident Ocean task. All six n8n executions were matched to this incident. The export decoded without errors; all 24 chapter starts, middles and ends were visually reviewed.

**Privacy:** only reviewed final-video frames and the final MP4 were published. Browser profiles, cookies, raw recordings and private preparation evidence stay outside the repository. No desktop, browser chrome, approval tokens, credential values, unrelated contacts, inboxes or personal contact fields are shown. Mapped customers are synthetic; their email addresses use `example.test` and they have no phone numbers.

**Preservation:** the previous `INC-F25410A828C8` incident, its 18 cases and its support task remain intact. Counts and the one-task result are scoped to the new recorded incident—not the entire location. No reset, deletion or unrelated workflow change was used for this recording.

## Retained launch and historical captures

| File | Source and type | What it proves | Current / historical | Privacy |
| --- | --- | --- | --- | --- |
| [relaycart-final-recovery.png](relaycart-final-recovery.png) | Real RelayCart browser screenshot, `http://127.0.0.1:8001`; native clip of technical and customer panels | Three signals, consumed approval, version-bound rollback, four passing checks; 18 affected, 1 confirmed, 16 pending, 1 follow-up; Acme/Ocean/Green Dental examples | Fresh launch capture, 2026-10-01; `INC-F25410A828C8` | Only seeded synthetic names and incident evidence; no browser chrome, credentials, or personal contact fields |
| [n8n-technical-response.png](n8n-technical-response.png) | Real n8n editor, IR 02 — Evidence and NIM Investigation; workflow `OvrKKVaPxERgQNnr` | Persisted signals + current snapshot → bounded request → real NIM / controlled failure branch → schema/evidence validation → deterministic policy | Fresh launch capture, 2026-10-01; installed 14-node graph matches export | Canvas only; no execution payload or credential editor. IR 02 chosen for clearer framing than the larger IR 04 graph |
| [n8n-ghl-impact-sync.png](n8n-ghl-impact-sync.png) | Real n8n editor, GHL 01 — Customer Impact Sync; workflow `lhpMBpbBH3j4BDjm` | PostgreSQL enqueue/claim, per-customer loop, lookup/create/update, remote-ID persistence, association, success/retry | Fresh launch capture, 2026-10-01; installed 24-node graph matches export | Wide canvas preserves the complete graph; open full resolution for node labels; no secrets or unrelated workflows |
| [n8n-ghl-feedback.png](n8n-ghl-feedback.png) | Real n8n editor, GHL 02 — Customer Recovery Feedback; workflow `tjUprwydaLuekcMg` | Outcome marker → conversation → fresh matching reply → outcome branch → task handling → persistence → transient tag cleanup | Fresh launch capture, 2026-10-01; installed 28-node graph matches export | Canvas only, no inbox, customer messages, execution bodies, or credentials; open full resolution |
| [ghl-service-cases.png](ghl-service-cases.png) | Real HighLevel Service Case list; unchanged copy of [Phase 3 capture](../phase3-ghl-service-case-list.png) | Native Custom Object, RelayCart Demo location, 18 synthetic cases, technical/customer columns | Historical Phase 3: `INC-57C615E767C3`; retained in commit `9e1fd37`. Not a capture of the current incident | Synthetic case list only; no contact emails, phones, unrelated records, credentials, or storage. Some columns are truncated by the original UI |
| [ghl-conversation-ai-workflow.png](ghl-conversation-ai-workflow.png) | Real native HighLevel workflow; unchanged copy of [Phase 3 capture](../phase3-ghl-workflow-ai-builder.png) | RelayCart — Customer Recovery Confirmation; Conversation AI action, checkout-working, still-broken, timeout and fallback branches; AI panel context | Historical Phase 3, retained in commit `9e1fd37`; current publication checked separately through the API | Workflow canvas only, no inbox/credentials. Does not show the original builder prompt or generation transcript |

At the October 1 launch, the HighLevel UI failed to render, so the older GHL screenshots were retained with explicit provenance. The October 3 recording resolved browser access and now supplies fresh native workflow and Service Case evidence. The historical files and [launch audit](launch-audit.md) remain unchanged for traceability; they do not describe the new recorded incident.

## Reproduction

The original October 1 static captures used an existing private Chromium profile with Playwright. The script below opens installed workflows, changes only viewport/zoom framing, and clips the actual dashboard. It never executes workflows, modifies data, or exports browser storage. It reproduces static views, not the full October 3 incident recording.

```bash
python scripts/capture-portfolio.py --profile /path/to/private/profile --chromium /path/to/chromium
```

Requires Playwright in the selected Python environment, Chromium, local RelayCart/n8n, and an existing n8n login. Browser profiles are private and must never be committed. Review outputs visually before publishing; no script can certify privacy from pixels alone.

The fresh PNGs were visually reviewed at capture and publication. Retained GHL files were also reviewed and copied byte-for-byte, preserving their evidence provenance. No optional inbox screenshots were retained. Older engineering evidence remains in [the parent index](../README.md).
