# Phase 3 verification

The accepted Phase 3 baseline signature was `INC-57C615E767C3`. The architecture correction replaced the live final signature with `INC-E37B035DE372` after the full Phase 2 regression. All records are synthetic and confined to RelayCart Demo. The baseline evidence below remains a historical account of the accepted Phase 3 run; the current correction results follow it.

| Check | Observed result |
| --- | --- |
| Credential and isolation | Agency PIT read worked; new isolated RelayCart Demo location was created; location PIT with required scoped capabilities read/wrote only that location |
| Contact seed | 30 mapped contacts; rerun created 0; no duplicate mapping |
| Custom object and association | Real Service Case schema, 14 fields, and Contact ↔ Service Case association verified by API and GHL UI |
| Affected subscribers | 18 checkout customers received cases; Acme and Ocean included; Green Dental excluded |
| Native Intake | Published and executed on newly created cases |
| Native Technical Recovery | Published and executed after technical `RECOVERED`; moved customer cases to `AWAITING_CONFIRMATION` and enrolled associated contacts |
| Native Conversation AI | Published Live Chat action executed for synthetic contacts; positive and negative branch tags executed |
| Positive | Acme: `RECOVERED` / `CONFIRMED_RESOLVED`; no escalation task |
| Negative | Ocean: `RECOVERED` / `NEEDS_FOLLOW_UP`; one unassigned human follow-up task |
| Timeout | Coffee Club AI action timed out; no outcome tag, no false resolution |
| Ambiguous | BookBox “I have not been able to test checkout yet.” did not resolve; pending case remained pending |
| Case idempotency | Repeat sync processed zero unchanged effects; deterministic keys and remote lookup protect retries |
| Failure and retry | Controlled GHL 503 made one effect `RETRY` while incident stayed `RECOVERED`; scheduled reconciliation later made it `SUCCEEDED` |

`./scripts/verify-phase2` passed 11 product-contract tests and 7 live n8n integration scenarios after Phase 3 backend integration. `docker compose exec -T api python scripts/phase3-signature` passed the real deploy/approval/rollback/18-case path. The final `scripts/phase3-verify-ghl` observed 18 current cases: 1 `CONFIRMED_RESOLVED`, 16 `AWAITING_CONFIRMATION`, 1 `NEEDS_FOLLOW_UP`; Green Dental had zero. Acme had zero support tasks and Ocean had exactly one. Re-running the provisioner created 0 contacts with 30 mapped; unchanged impact sync processed 0 effects. Both Phase 3 n8n workflows were confirmed active.

An intermediate final-demo attempt exposed a native workflow defect: its generated “No Condition Met” action tagged silent contacts for follow-up. That run was rejected as evidence. The native action was removed and saved; a scoped cleanup deleted that failed incident's 18 test cases and 17 erroneous tasks without touching contacts or another location. The fresh incident above kept all 16 nonresponders awaiting confirmation. This is the reason the fallback ends pending rather than escalating automatically. It is deliberately conservative and never resolves an ambiguous reply.

After the final audit, a second exact-scope cleanup removed 49 superseded synthetic Service Cases from two older test incidents and one old test task. The isolated GHL Service Cases list now contains exactly the 18 final-incident records; no mapped contacts or current cases were removed. The [case-list screenshot](evidence/phase3-ghl-service-case-list.png) shows the resulting single-page view.

The actual Workflow AI Builder prompt was:

> Create a draft contact-based workflow named RelayCart — Customer Recovery Confirmation for a synthetic B2B SaaS demo. Run it only after an associated Service Case has Technical Status RECOVERED. Use the Conversation AI Workflow Action on Live Chat to ask: We have restored and verified RelayCart checkout. Please retry checkout. Is it working normally for you? If the customer clearly confirms working, update the associated Service Case Customer Status to CONFIRMED_RESOLVED and set Customer Confirmed At. If still broken, set NEEDS_FOLLOW_UP and create a human support task. On timeout leave AWAITING_CONFIRMATION. Ambiguous replies require human follow-up. Never diagnose or remediate the technical incident. Keep the workflow a draft. Never send SMS, email, or WhatsApp.

It generated a useful initial Contact conversation/branch graph. Review corrected inappropriate trigger assumptions, association handoff, field mappings, timeout/fallback behavior, and task assignment. The isolated location has no staff user, so GHL's native Add Task action skipped; a scoped, idempotent API task replaced it.

The cloud location cannot call localhost directly, so GHL native outcome tags plus a 60-second local poll are the feedback path. This is a deliberate local-demo limitation. There is no real messaging, production IAM, or production availability claim.

## Architecture correction: current live state

GHL 01 (`lhpMBpbBH3j4BDjm`, 24 active nodes) now performs Postgres effect enqueue/claim, a three-at-a-time per-customer loop, direct credential-backed HighLevel case search/create/update and association calls, ID persistence, and success/retry writes. GHL 02 (`tjUprwydaLuekcMg`, 28 active nodes) now reads contact outcome tags and post-recovery inbound messages, branches by outcome, updates the case, persists feedback, ensures one unassigned task when needed, and clears only transient result tags. `app/customer_ops.py` is now an audit-only helper; `/customer-ops/sync` and `/customer-ops/poll-feedback` were removed. The workflow exports are generated from [the checked-in builder](../scripts/build-phase3-workflows) and contain only safe credential references.

The corrected live signature is `INC-E37B035DE372`: 18 checkout subscriber cases, all technical status `RECOVERED`; Acme `CONFIRMED_RESOLVED` with zero tasks; Ocean `NEEDS_FOLLOW_UP` with one task; 16 `AWAITING_CONFIRMATION`; Green Dental zero. `python3 scripts/ghl-provision seed` created zero contacts and mapped the existing 30. Two duplicate manual sync deliveries left `18` successful effects and `18` distinct remote IDs. Clearing Coffee Club's local remote ID and retrying restored the same ID (`6abd853438ba68d3324b7dcb`) without creating a case. The `simulate_503=1` manual workflow fixture moved Mosaic Works to `RETRY` with HTTP 503 while the technical incident remained `RECOVERED`; the scheduled run returned the effect to `SUCCEEDED`.

`./scripts/verify-phase2` passed after the Python reduction: 11 product tests, 5 AI-validator tests, and 7 live n8n integration scenarios. The first post-regression signature driver run timed out while waiting for the expected six 30-second recovery-update batches; the last three effects succeeded shortly afterward. The driver wait was increased from 120 to 300 seconds. API verification of the same live run then passed all 18 cases, both customer outcomes, both task counts, and the unaffected control.

The new incident exposed an important safety case before the final run: an old Conversation AI result tag could be seen on a newly recovered case. An unverified intermediate Acme/Ocean outcome and its single new-incident task were explicitly reversed. GHL 02 now requires a matching customer inbound message newer than `recovered_at` before accepting either outcome, and clears a stale marker without recording feedback. The final run had no feedback before new test replies, then recorded only the two fresh Live Chat answers. The superseded synthetic incident cases were deleted by exact incident ID only after the replacement passed. The older GHL screenshots above show the accepted baseline incident; the current n8n export-rendered graphs are [Customer Impact Sync](evidence/phase3-n8n-customer-impact-graph.png) and [Customer Recovery Feedback](evidence/phase3-n8n-customer-feedback-graph.png). These graphs are faithful renderings of the checked-in node/edge exports, not captures of the n8n editor UI.

The account-wide audit also found 10 partial cases from four temporary production-demo incidents created by the Phase 2 regression while GHL 01 was active. Their exact incident IDs were absent locally, all 10 records had the RelayCart demo marker and deterministic keys, and no matching support tasks existed. Only those 10 cases were removed. The Phase 2 verification runner now deactivates just the two RelayCart GHL workflows for its fixture run and restores their prior active state on exit; its deactivate/activate commands were checked live. A final account-wide GHL search showed exactly 18 Service Cases, all for `INC-E37B035DE372`, with the 16/1/1 customer-status split.
