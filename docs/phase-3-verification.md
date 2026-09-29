# Phase 3 verification

The final signature incident was `INC-57C615E767C3`. The completion report records the commit SHA. All records below are synthetic and confined to RelayCart Demo.

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

The actual Workflow AI Builder prompt was:

> Create a draft contact-based workflow named RelayCart — Customer Recovery Confirmation for a synthetic B2B SaaS demo. Run it only after an associated Service Case has Technical Status RECOVERED. Use the Conversation AI Workflow Action on Live Chat to ask: We have restored and verified RelayCart checkout. Please retry checkout. Is it working normally for you? If the customer clearly confirms working, update the associated Service Case Customer Status to CONFIRMED_RESOLVED and set Customer Confirmed At. If still broken, set NEEDS_FOLLOW_UP and create a human support task. On timeout leave AWAITING_CONFIRMATION. Ambiguous replies require human follow-up. Never diagnose or remediate the technical incident. Keep the workflow a draft. Never send SMS, email, or WhatsApp.

It generated a useful initial Contact conversation/branch graph. Review corrected inappropriate trigger assumptions, association handoff, field mappings, timeout/fallback behavior, and task assignment. The isolated location has no staff user, so GHL's native Add Task action skipped; a scoped, idempotent API task replaced it.

The cloud location cannot call localhost directly, so GHL native outcome tags plus a 30-second local poll are the feedback path. This is a deliberate local-demo limitation. There is no real messaging, production IAM, or production availability claim.
