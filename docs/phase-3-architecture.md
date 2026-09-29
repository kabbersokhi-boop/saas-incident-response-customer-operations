# Phase 3 architecture

RelayCart and PostgreSQL remain authoritative for subscriptions and technical incidents. n8n's four Phase 2 workflows still detect, investigate, approve, remediate, and verify. Phase 3 adds two narrow n8n reconciliations and customer operations in the isolated **RelayCart Demo** HighLevel location (`CP8Flhg4iyKzzm6vlOgu`). No other location is in scope.

```text
RelayCart service subscription + technical incident
  → GHL 01 — Customer Impact Sync (30-second schedule or manual webhook)
  → deterministic PostgreSQL effect ledger
  → associated Service Cases for the 18 checkout subscribers
  → native Service Case Intake and Technical Recovery workflows
  → associated Contact enters Customer Recovery Confirmation
  → Conversation AI Live Chat outcome tags
  → GHL 02 — Customer Recovery Feedback (30-second schedule)
  → customer-only case status, feedback record, and (if needed) support task
  → RelayCart dashboard projection
```

The ledger uniquely identifies each effect by incident and customer key, records its desired technical state, remote record ID, attempts, and retry time. A temporary GHL error becomes `RETRY`; it cannot roll back, close, or reopen a technical incident. A transaction-scoped advisory lock protects concurrent scheduled and manual reconciliations. Case lookup by deterministic key repairs a failure between remote creation and local ID persistence. Contact mappings are explicit IDs, not name matching.

The cloud HighLevel location cannot reach localhost n8n. Native GHL workflows mark the result with two transient `relaycart-*` contact tags; local n8n polls those synthetic contacts, updates the corresponding Service Case, records feedback separately from the technical incident, and clears only those outcome tags. A new incident therefore does not inherit an old answer. This is a local-demo transport choice, not a production webhook design.

The isolated location has no staff user. HighLevel's native Add Task workflow action rejected an unassigned task, so the negative branch uses the API reconciler to create one idempotent, visible, unassigned contact task instead. No real customer channel is used. The local API and approval page are not production-authenticated.

The three published native workflows are:

| Workflow | Object | Trigger | Responsibility |
| --- | --- | --- | --- |
| RelayCart — Service Case Intake | Service Case | Created | Internal intake note and visible customer-operations handoff |
| RelayCart — Technical Recovery | Service Case | Technical Status becomes RECOVERED | Set Customer Status to AWAITING_CONFIRMATION and enroll associated Contact |
| RelayCart — Customer Recovery Confirmation | Contact | `relaycart-recovery-ready` tag or association enrollment | Conversation AI Live Chat question; positive/negative tags; safe timeout and fallback |

The Recovery Confirmation draft was genuinely generated with HighLevel Workflow AI Builder. It supplied the broad conversation flow, but initially selected unsuitable triggers and incomplete field/action mappings. Engineering review corrected the trigger, association handoff, customer-status ownership, no-condition/timeout behavior, and task handling before publication. See [verification](phase-3-verification.md).
