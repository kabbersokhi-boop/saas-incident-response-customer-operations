# Phase 3 architecture

RelayCart and PostgreSQL remain authoritative for subscriptions and technical incidents. n8n's four Phase 2 workflows still detect, investigate, approve, remediate, and verify. Phase 3 adds two n8n-orchestrated customer integrations in the isolated **RelayCart Demo** HighLevel location (`CP8Flhg4iyKzzm6vlOgu`). No other location is in scope.

```text
RelayCart service subscription + technical incident
  → GHL 01 — Customer Impact Sync (30-second schedule or manual webhook)
  → deterministic PostgreSQL effect ledger
  → associated Service Cases for the 18 checkout subscribers
  → native Service Case Intake and Technical Recovery workflows
  → associated Contact enters Customer Recovery Confirmation
  → Conversation AI Live Chat outcome tags
  → GHL 02 — Customer Recovery Feedback (60-second schedule)
  → customer-only case status, feedback record, and (if needed) support task
  → RelayCart dashboard projection
```

GHL 01 itself enqueues subscribed customers with an atomic Postgres upsert, claims up to three due effects with `FOR UPDATE SKIP LOCKED` and a three-minute lease, and loops over them. Its credential-backed HTTP nodes search for a deterministic case key, visibly branch between create and update, ensure the real association, and mark `SUCCEEDED` or `RETRY`. A known remote ID is preferred while a missing local ID is repaired by key search. The database retains the unique `(incident_id, customer_key, effect_type)` constraint, explicit contact IDs, desired technical state, attempts, and retry time. A GHL error cannot change the technical incident. The manual webhook supports a scoped `simulate_503=1` fixture.

The cloud HighLevel location cannot reach localhost n8n. Native GHL workflows mark the result with two transient `relaycart-*` contact tags. GHL 02 loops over recovered cases, reads the tags and conversation, and requires a matching inbound reply newer than the incident's verified recovery time. This guards against an old answer being reused for a new incident. It then branches to update only customer status, atomically records feedback, ensures one support task on the negative path, and clears only transient outcome tags. Silent and ambiguous contacts stay pending. This is a local-demo transport choice, not a production webhook design.

The isolated location has no staff user. HighLevel's native Add Task workflow action rejected an unassigned task, so GHL 02 reads existing tasks and creates one idempotent, visible, unassigned contact task through a credential-backed HTTP node. FastAPI retains only the RelayCart product/demo surface, a read-only customer-recovery projection, and audit helpers; it no longer reconciles GHL. No real customer channel is used. The local API and approval page are not production-authenticated.

The three published native workflows are:

| Workflow | Object | Trigger | Responsibility |
| --- | --- | --- | --- |
| RelayCart — Service Case Intake | Service Case | Created | Internal intake note and visible customer-operations handoff |
| RelayCart — Technical Recovery | Service Case | Technical Status becomes RECOVERED | Set Customer Status to AWAITING_CONFIRMATION and enroll associated Contact |
| RelayCart — Customer Recovery Confirmation | Contact | `relaycart-recovery-ready` tag or association enrollment | Conversation AI Live Chat question; positive/negative tags; safe timeout and fallback |

The Recovery Confirmation draft was genuinely generated with HighLevel Workflow AI Builder. It supplied the broad conversation flow, but initially selected unsuitable triggers and incomplete field/action mappings. Engineering review corrected the trigger, association handoff, customer-status ownership, no-condition/timeout behavior, and task handling before publication. See [verification](phase-3-verification.md).
