# RelayCart runbook

## Startup and prerequisites

```sh
cp .env.example .env                 # only on initial setup; preserve existing private values
docker compose up --build -d
./scripts/connect-n8n
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U relaycart -d relaycart < n8n/schema.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U relaycart -d relaycart < n8n/phase3-schema.sql
```

RelayCart: `http://127.0.0.1:8001`. Existing n8n: `http://localhost:5678`. Shared network: `relaycart-n8n`; API `relaycart-api:8000`, database `relaycart-postgres:5432`. The repository does not provision n8n. The demonstrated version is 2.39.8.

Standalone RelayCart needs only Docker. Live automation requires Postgres and NVIDIA NIM header-auth credentials in n8n. Customer integration also requires a location-scoped GHL token for contacts, custom-object records, associations, conversations/messages, tags, and tasks. Keep private values in ignored runtime configuration, never exports or screenshots. Use only RelayCart Demo (`CP8Flhg4iyKzzm6vlOgu`); another reviewer must provision a separate synthetic location and update IDs.

## Workflow import/update

Import six JSON files from `n8n/workflows` through the editor. They are inactive on import. Rebind Postgres, NIM, and GHL credential references. Update Execute Workflow IDs in IR 04/IR 05/other sub-workflow references to imported local IDs; update GHL location, object/association, and contact/native-workflow mappings for another environment. Inspect every HTTP destination before activation.

The local `scripts/n8n-workflow-api` uses an existing stored API key inside the n8n container without printing it. It is a convenience for this SQLite-backed instance, not a general n8n deployment API bootstrap. For an exact existing workflow update:

```sh
./scripts/n8n-workflow-api status tjUprwydaLuekcMg
./scripts/n8n-workflow-api deactivate tjUprwydaLuekcMg
./scripts/n8n-workflow-api update tjUprwydaLuekcMg n8n/workflows/07-ghl-customer-feedback.json
./scripts/n8n-workflow-api activate tjUprwydaLuekcMg
```

Do not update unrelated workflows in the shared instance. The six RelayCart IDs are recorded in Phase 4 verification. Native GHL workflow provisioning is not fully automated; the existing published workflow and Phase 3 setup records are prerequisites for complete reproduction.

## Healthy, broken, approval, stale approval

Use the dashboard to create a baseline checkout/order, deploy `v1.8.2`, probe health, and run the failing checkout. Wait for investigation; open `http://localhost:5678/webhook/phase2/approval/pending`. Review exact source/target and expiry before choosing approve or reject. Recovery requires four checks.

For stale approval, deploy `v1.8.3` before approving the pending `v1.8.2 → v1.8.1` proposal. Expect HTTP 409 and unchanged `v1.8.3`. Reset/cleanup this test before preparing customer evidence.

## Proof suite

```sh
./scripts/phase4-proof public
./scripts/phase4-proof technical
./scripts/phase4-proof ghl
```

Public mode is credential-free. Technical mode snapshots this project's DB to a private temporary directory, pauses the five independently triggered RelayCart workflows, waits for all six workflows to quiesce, runs regression/proof tests, then restores the snapshot and previous flags. IR 05 is an invoked sub-workflow; its stored flag is left untouched. Exact remote case inventory is compared before/after. Run with no concurrent operator changes. External NIM calls and n8n execution history remain; do not expose execution bodies containing approval tokens. A failed run preserves its private backup for diagnosis.

GHL mode requires a clean 18-case current incident, Acme/Ocean outcomes, and prepared Coffee timeout/BookBox ambiguous conversations. It exercises 503/retry, lost local ID, stale markers, and repeated Ocean feedback. Verify exit 0 and the final inventory. A failed proof is not a pass.

The original `./scripts/verify` (four Phase 1 tests) and `./scripts/verify-phase2` reset local demo records. The latter pauses/restores the two GHL integrations but does not preserve a final local incident. Prefer the wrapper for a prepared demonstration.

## Fresh final customer demo / reset

Reset removes local technical incidents/effects/feedback; it does **not** delete cloud Service Cases. Record the exact old incident ID before reset. A fresh demo may temporarily have old and new remote cases.

```sh
docker compose exec -T api python scripts/phase3-signature
docker compose exec -T api python scripts/phase3-live-chat-test acme-bikes working
docker compose exec -T api python scripts/phase3-live-chat-test ocean-apparel-02 broken
docker compose exec -T api python scripts/phase3-live-chat-test coffee-club-03 timeout
docker compose exec -T api python scripts/phase3-live-chat-test bookbox-06 ambiguous
docker compose exec -T api python scripts/phase3-verify-ghl
```

The signature driver approves the real synthetic proposal in memory; use the UI for the human presentation. Allow up to five minutes for 18-case recovery fanout. Allow the native AI timeout and the 60-second feedback poll to finish before auditing.

Only after the replacement passes, dry-run exact-scope removal of the superseded incident:

```sh
docker compose exec -T api python scripts/phase3-purge-test-incident INC-EXACT-OLD-ID
# Review the exact synthetic cases/tasks, then repeat with --execute.
```

Deletion is remote and not automatically recoverable. The helper refuses a still-local incident and validates synthetic case identity. It does not remove contacts. Never perform account-wide cleanup.

## Diagnosis and shutdown

| Symptom | Inspect |
| --- | --- |
| API unreachable | `docker compose ps`; API logs; port 8001; Postgres health |
| No incident | IR 01 active; network probe; valid event contract; application log poll |
| No assessment/proposal | IR 02 execution; persisted assessment status; policy requires both failures and a prior healthy release |
| Approval blocked | Expiry, prior consumption, revision, current source release; do not bypass the gate |
| Rollback succeeded, not recovered | Four persisted verification checks; checkout-fault fixture; exact expected release |
| GHL cases delayed | GHL 01 effect state, lease, last error, next attempt; batch size three every 30 seconds |
| Outcome stays pending | GHL 02 active; native tags; newer matching inbound reply; ambiguity; provider/API failure |
| Missing support task | Ocean negative reply, task read/create execution; exact incident title |

Disable a temporary business fixture with `curl -fsS -X POST http://127.0.0.1:8001/demo/checkout-fault -H 'Content-Type: application/json' -d '{"enabled":false}'`. `/demo/reset` also clears it but deletes incident evidence.

Shutdown RelayCart with `docker compose stop`. Keep the database volume; do not use `down -v` for routine shutdown. Pause the six RelayCart workflows if intentionally stopping their dependencies; preserve their prior states for restart. Leave unrelated shared n8n services alone.
