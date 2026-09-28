# Phase 2 architecture

## Scope and status

Phase 2 adds local technical incident response around the synthetic RelayCart service. It does not add GoHighLevel/customer operations, customer messaging, or production identity controls. Consult [verification](phase-2-verification.md) for the live scenarios and limitations.

## Components and network

```text
RelayCart API ─┐
               ├── relaycart-n8n bridge network ── n8n
RelayCart DB ──┘
                     │
                     └── NVIDIA NIM (advisory HTTP request)
```

The existing n8n container is joined to the Compose bridge network `relaycart-n8n` by `scripts/connect-n8n`. Inside that network, use `http://relaycart-api:8000` and `relaycart-postgres:5432`; host port `8001` is for browser/host access and is not the container-to-container route. The helper starts this repository's API and Postgres containers, connects n8n only when needed, and probes both addresses from inside n8n. It does not recreate the existing n8n container.

Apply the incident state schema after the Compose database is available:

```sh
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U relaycart -d relaycart < n8n/schema.sql
```

The database is the source of durable event and incident records. RelayCart provides deterministic product behavior and a read-only incident projection. The active n8n workflows own validation, correlation, severity, evidence orchestration, AI request/validation, approval, remediation, and recovery checks. `IR 05 - Recovery Verification` is an Execute Workflow sub-workflow; both passing and failing business-verification runs were exercised and their persisted checks inspected. See [verification](phase-2-verification.md).

## Event and incident terms

- An **event** is one normalized operational observation with a stable `event_id`.
- A **signal** is an event that may contribute to incident detection.
- An **incident** is the durable correlated unit of investigation and response.
- An **evidence item** is a bounded, persisted observation with an incident-local reference such as `E1`.
- An **AI assessment** is an advisory, schema-validated summary tied to a persisted evidence set.
- A **proposal** names a specific permitted action and exact source/target versions.
- An **approval** is a single-use, expiring human decision bound to that proposal.
- A **remediation attempt** records the request and result of a proposed action.
- A **verification** is a set of post-action checks. Recovery requires all required checks, not just a successful rollback HTTP response.

## Canonical event shape

The normalized event contract is:

```json
{
  "event_id": "evt-relaycart-deployment-123",
  "source": "relaycart",
  "event_type": "deployment.completed",
  "service": "checkout-api",
  "environment": "production-demo",
  "occurred_at": "2026-09-28T14:15:00Z",
  "correlation_hint": "deployment-123",
  "severity_hint": null,
  "metadata": {
    "version": "v1.8.2",
    "outcome": "completed"
  }
}
```

Only allowlisted types are intended: `deployment.completed`, `health.failed`, `checkout.failed`, and `manual.test`. The schema enforces the stable event ID primary key, required source/type/service/environment/time, allowed severity hints, and object-shaped metadata. Keep secrets, credentials, customer data, and unbounded raw logs out of metadata. The deployed `IR 01 - Event Intake and Correlation` workflow accepts `POST http://localhost:5678/webhook/ir/events` and polls `http://relaycart-api:8000/logs` every 15 seconds; see the actual test evidence in [verification](phase-2-verification.md).

## Persisted state

`n8n/schema.sql` defines `ir_events`, `ir_incidents`, `ir_incident_events`, `ir_evidence`, `ir_assessments`, `ir_proposals`, `ir_approvals`, `ir_remediation_attempts`, `ir_verification_checks`, and `ir_poll_state`. `event_id` is a primary key, incident/event links are unique, only one nonterminal incident can exist for a service/environment pair, evidence keys are unique per incident, proposal revisions are unique per incident, and an approval is unique per proposal. These database constraints complement workflow checks and provide atomic duplicate protection.

The state vocabulary in the schema is `OPEN`, `INVESTIGATING`, `WAITING_FOR_APPROVAL`, `REMEDIATING`, `VERIFYING`, `NEEDS_ATTENTION`, `RECOVERED`, and `RESOLVED`. A recovered technical incident has passed its required recovery checks; `RESOLVED` is reserved for a later lifecycle and is not required to demonstrate customer follow-up.

Severity is deterministic, restricted to SEV-1/2/3, and not assigned by the model. The fixture outage is expected to classify as SEV-2; final rules and observed classifications must be reported with the live workflow evidence.

## Trust and authority boundaries

NVIDIA NIM receives bounded evidence and returns an advisory assessment. It cannot call tools or invoke remediation. Event/log text is untrusted and may contain hostile instructions. The workflow validates output shape, enums, and evidence references, then independently applies policy. Human approval is required for rollback. The rollback request is bound to a source and target version and must check the live source before acting. Recovery must independently establish the expected version, healthy state, successful synthetic checkout, and retrievable created order.

The public workflow exports carry only local credential ID/name references, not encrypted credential payloads or secrets. A different n8n instance must rebind its own credentials. The NIM key is kept in private runtime configuration and must never be printed or committed. See the verification record for the exercised controls.

## Approval surface and rollback replay

The local approval page is served at <http://127.0.0.1:5678/webhook/phase2/approval/pending>; explicit decisions are posted to `/webhook/phase2/approval/decision`. Loading or refreshing the page is read-only. The page is local and unauthenticated, so it is not production IAM. It displays the exact action, source and target versions, evidence summary, and expiry. The decision token is short-lived and single-use; never copy it into logs, screenshots, or repository artifacts.

RelayCart's `rollback_requests` table adds an atomic unique `request_id` ledger for rollback calls. Replaying the same request with the same source and target returns the stored result after a lost response; reusing the request ID with a different binding is rejected. That API-level idempotency complements n8n's single-use proposal approval. A rollback response still has to pass all four recovery checks before the incident can become `RECOVERED`.
