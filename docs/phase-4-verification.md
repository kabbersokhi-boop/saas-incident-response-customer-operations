# Phase 4 proof record

Launch follow-up: the [2026-10-01 location-wide audit](evidence/portfolio/launch-audit.md) found and removed 22 older orphan RelayCart tasks that the current-contact audit below could not see. Cases and contacts remained unchanged. The strengthened verifier now searches the whole location and proves one current Ocean task and zero older RelayCart tasks. The original engineering observations below remain historical evidence.

Verified on 2026-10-01 in the local synthetic environment. Starting/public baseline: `c5d83a5c3ae6894adba20763a63de8ba0e369276` (`Move GHL customer orchestration into n8n`). Git fetch found no later correction and the starting tree was clean. Architecture remains unchanged.

## Baseline and reproduction

| Command | Observed |
| --- | --- |
| `./scripts/verify` | 4 passed; exit 0 |
| `./scripts/verify-phase2` | 11 product tests, 5 AI-validator tests, 7 live n8n tests passed; exit 0; both GHL workflows restored active |
| `docker compose exec -T api pytest -q -s tests/test_phase4_n8n.py` | 8 passed in 149.27 seconds; no skips |
| `./scripts/phase4-proof public` | 9 Node tests passed; workflow/syntax/secret checks passed; 16 fixtures dry-run, zero provider requests |
| `./scripts/phase4-proof technical` | Exit 0; 11 product tests, 5 evaluator tests, 7 live tests (112.31 seconds), 8 Phase 4 tests (168.54 seconds); exact remote inventory and six previous active states restored; local DB restored |
| `docker compose exec -T api python scripts/phase3-signature` | New signature `INC-F25410A828C8`; real approval/rollback; all four checks; 18 synced recovered cases; exit 0 |
| `docker compose exec -T api python scripts/phase3-verify-ghl` | Acme recovered/resolved with 0 tasks; Ocean recovered/follow-up with 1 task; 16 pending; Green Dental 0 |
| `./scripts/phase4-proof ghl` | Exit 0; durable 503/retry, scheduled success, same-ID repair, stale/ambiguous marker cleanup, positive/negative replay, unchanged 18-case inventory; strengthened current GHL audit passed |

The Phase 1 runner resets local incident state. It was initially run before a snapshot, so the accepted local incident was replaced with a fresh final signature; cloud records remained intact. The original signature remains historical evidence. The Phase 4 technical wrapper now snapshots/restores the project DB and compares exact remote case inventory around technical fixtures.

## Adversarial matrix

| Scenario | Expected | Observed | Result | Evidence |
| --- | --- | --- | --- | --- |
| Duplicate storm | One event and incident effect | 20 concurrent failure-signal submissions: 1 accepted, 19 duplicates; SQL counts 1 event, 1 link, 1 incident | PASS | `tests/test_phase4_n8n.py::test_failure_signal_storm_has_one_durable_incident_effect` |
| Signal correlation | Distinct signals, one incident | Deployment, health, checkout share an incident; earlier healthy deployment remains context | PASS | `tests/test_phase2_n8n.py::test_deployment_health_and_checkout_correlate_and_project_one_incident` |
| AI unavailable | Persist incident; no autonomous action | Timeout and HTTP 503 fixtures persist unavailable; WAITING_FOR_APPROVAL; attempts 0 | PASS | Phase 4 parametrized live test |
| Malformed AI | Reject assessment, preserve incident | Invalid JSON becomes invalid; no remediation attempt | PASS | `malformed_json` live fixture |
| Invalid AI enum/schema | Reject unsupported values | `confidence=certain` becomes invalid; no action | PASS | `schema_invalid` live fixture; evaluator unit tests |
| Invalid reference | Reject E99 | Validation errors name E99; incident and human gate survive | PASS | `unknown_evidence_ref` live fixture |
| Prompt injection | Untrusted evidence cannot authorize rollback | Actual NIM assessment valid; malicious log persisted; release remains v1.8.2; WAITING_FOR_APPROVAL; attempts 0 | PASS | Real provider call in Phase 4 injection test |
| Approval rejection | No rollback; terminal decision | Real proposal REJECTED; replay 409; version unchanged; attempts 0 | PASS | Phase 4 real rejection + Phase 2 single-use assertions |
| Approval expiry | Expired proposal cannot execute | Real proposal given two-second expiry; EXPIRED; version unchanged; attempts 0; normal 15-minute policy unchanged | PASS | Phase 4 controlled expiry |
| Stale approval | Preserve newer release | v1.8.2 proposal attempted after v1.8.3; HTTP 409; stale attempt; no rollback event | PASS | Phase 2 stale-source live test |
| Successful rollback / broken checkout | Must not recover | v1.8.1 and health pass; checkout/read-back fail; NEEDS_ATTENTION | PASS | Phase 2 business-failure live test |
| GHL 503 / retry | Durable retry, independent technical state | Mosaic effect RETRY with persisted HTTP 503; technical RECOVERED; scheduled run SUCCEEDED | PASS | `scripts/phase4-ghl-proof` exit 0 |
| Remote ID recovery | Find same case, repair local ID | Coffee local ID set NULL; deterministic lookup restores the same remote ID; exact inventory unchanged | PASS | `scripts/phase4-ghl-proof` exit 0 |
| Customer still broken | One task; technical stays recovered | Ocean fresh negative and repeated marker: NEEDS_FOLLOW_UP; one task; one feedback; marker cleared; incident RECOVERED | PASS | Current GHL audit and live replay |
| Timeout / ambiguity | No false closure | Coffee silent and BookBox “I have not been able to test checkout yet.” remain AWAITING_CONFIRMATION | PASS | Current native test conversations; fresh-reply node tests |
| Stale marker | Require newer matching inbound evidence | Coffee/BookBox positive tags cleared; no matching fresh positive reply, no feedback, both pending; old/boundary/outbound cases pass actual-node tests | PASS | `tests/workflow-safety.test.mjs`; live GHL proof |
| Phase 2 / GHL isolation | No stray cases; restore states | Exact 18 remote case IDs/keys/statuses unchanged; six previous flags and original local demo DB restored | PASS | `scripts/phase4-proof technical` exit 0 |

The fixture paths run the installed workflows, not a second incident engine. Provider fixtures are restricted to `manual.test`. The injection scenario uses a real advisory request; its proof is architectural containment, not a claim that prompt injection is universally solved.

## Narrow defects repaired

The accepted feedback-node code returned `fresh=true` for a positive marker plus “It is not working.” Phase 4 now checks the latest relevant inbound reply, excludes uncertainty, and rejects negation/negative evidence for positive closure. Opposite/conflicting markers do not grant closure.

A replayed outcome previously made the PostgreSQL `ON CONFLICT DO NOTHING RETURNING` node emit no item, which could stop tag cleanup. The query now returns the existing feedback row on conflict. The same graph retains its 28 nodes; repeated negative feedback follows the existing task lookup and cannot create a second task in the tested replay.

Four Node tests execute the **actual checked-in node JavaScript**. Early proof-harness failures (incorrect SQL join and unsupported fixture mode) were corrected and the entire eight-case live suite rerun; those attempts were not counted as passes.

## n8n runtime versus exports

n8n 2.39.8, existing local container, shared `relaycart-n8n` network. Only the six RelayCart workflows are in scope; unrelated workflows remain untouched.

| Workflow | ID | Nodes | Final state |
| --- | --- | --- | --- |
| IR 01 | `lYDxGst3gQbuhRrn` | 12 | Active |
| IR 02 | `OvrKKVaPxERgQNnr` | 14 | Active |
| IR 04 | `hRUiukB454KlQ2N6` | 35 | Active |
| IR 05 | `2jX0JueG8G7HYrot` | 15 | Stored active flag; invoked as sub-workflow |
| GHL 01 | `lhpMBpbBH3j4BDjm` | 24 | Active |
| GHL 02 | `tjUprwydaLuekcMg` | 28 | Active |

Exports have `active:false` or omit `active`; import is intentionally inactive. All six runtime graphs match export node parameters and connections exactly. Credential references name Postgres, NVIDIA NIM, and RelayCart Demo HighLevel PIT without containing values.

IR 05 has no independent schedule/webhook. This n8n version rejects public-API activation for that sub-workflow. An initial preserving-wrapper attempt encountered this API restriction before tests, restored the DB, and was corrected to leave IR 05's flag untouched while pausing/quiescing its parents. Its original stored flag was restored with the local n8n CLI. Actual sub-workflow invocation is proven by the recovery tests; a stored flag is not an independent active trigger.

## Current GHL evidence and cleanup

Final signature: `INC-F25410A828C8`. The earlier `INC-E37B035DE372` and `INC-57C615E767C3` belong to historical Phase 3 evidence.

- 30 mapped synthetic contacts, all `@example.test`, no mapped phone numbers.
- 18 current Service Cases; technical RECOVERED on all; 16 awaiting confirmation, Acme resolved, Ocean follow-up.
- Green Dental has no checkout case; Acme has zero current incident tasks; Ocean has exactly one.
- The flagship native customer workflow is published (`0c12cdc2-b90d-4c97-b9a7-40531518e3b6`). Real association checked by API.
- Seven additional unmapped location contacts were discovered; some have phone data. Their identities/data are outside the seeded project and are not published or deleted. Do not claim the entire location contains only synthetic data.
- After the fresh signature passed, exact-scope cleanup removed the superseded incident's 18 demo cases and one task. No contacts were removed. Remote deletion is not automatically recoverable; the historical evidence remains in Git.

## NIM reliability review

Model remains `openai/gpt-oss-20b`; no benchmark or model migration was added. The n8n execution audit for this Phase 4 session found 14 real advisory provider executions across regression, proof-harness retries, and the final signature: 12 valid, 2 invalid, 0 unavailable. The two real invalid responses failed hypothesis shape and top-level schema validation respectively. Completed request durations ranged from 4,972 to 19,041 ms. Real injection runs were valid and remained approval-gated; the final signature assessment was valid.

Controlled timeout/503/invalid fixtures make no provider requests and independently prove degradation. No extra evaluation batch was requested. Historical 16-case evaluation had four provider/transport failures and one invalid schema; it remains historical, not current availability or accuracy evidence. Fourteen local execution observations do not establish provider reliability or causal accuracy.

## Security, visual evidence, and claims

`scripts/check-public --history` passed for tracked/proposed files and 111 reachable pre-Phase-4 historical blobs. It checks high-confidence credential patterns and exact private token values from local ignored configuration when available. Workflow structure, safe credential references, and absence of literal authorization/cookie headers passed separately. This is a focused scan, not a certification that all possible secrets can be detected. Retained portfolio screenshots were visually reviewed; older inbox captures containing unmapped contacts were removed from the current tree.

Real n8n editor captures were obtained for GHL 01, GHL 02, and IR 04. Current RelayCart evidence is distinct from historical GHL screenshots. A fresh Workflow AI Builder interaction screenshot could not be obtained: the existing authenticated GHL shell rendered, but its workflow micro-frontend iframe remained blank in the available browser sessions. The workflow was not rebuilt for a screenshot. The retained historical image shows the AI panel and RelayCart workflow context, not a visible original prompt interaction. The documented Phase 3 builder prompt is a historical implementation record.

No video was created; screenshots and the executable demo script cover the presentation without adding recording infrastructure. The main README avoids production-ready, enterprise-grade, autonomous recovery, guaranteed availability, and AI accuracy claims.

The final schema audit found 14 Service Case fields and the expected custom association. Across all 30 mapped contacts there is exactly one task, the current Ocean follow-up, and zero older RelayCart tasks. Both removed Python orchestration endpoints return HTTP 404. RelayCart is healthy v1.8.1 with the checkout-fault fixture disabled.
