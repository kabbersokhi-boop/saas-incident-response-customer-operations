# Interview guide

**Why n8n rather than Python orchestration?** The incident and GHL processes are visible as stateful workflows: reads, policy, approvals, HTTP calls, branches, and retries. FastAPI models the product and exposes read-only projections. Its customer-ops module is an audit helper; the old orchestration endpoints return 404.

**Why PostgreSQL with n8n?** Webhook retries, concurrent deliveries, workflow restarts, and remote write failures outlive an execution. Unique constraints, atomic claims, and persisted attempts provide correctness beyond a visual execution counter.

**Why doesn't AI decide severity or execute rollback?** Its diagnosis may be unavailable, wrong, or influenced by evidence. Severity and rollback eligibility are deterministic. Valid JSON is advice, not permission; only an exact human decision crosses the action boundary.

**Why bind source and target versions?** An operator approved a specific state transition. If a newer release appears, executing the older action would authorize something the operator never reviewed. n8n and the API both check this binding.

**Why aren't `/health` and rollback HTTP 200 enough?** Health can be green while checkout fails. Rollback can change a release without restoring business behavior. Recovery requires expected version, healthy service, successful order creation, and matching order read-back.

**Why separate GHL technical/customer status?** Global checks cannot verify every merchant's setup. Acme can confirm success while Ocean needs a support task; neither answer independently authorizes a production rollback.

**How do duplicates behave?** Event ID is a durable primary key. Twenty concurrent deliveries yield one event and one incident link. Customer effects are unique by incident/customer/type; remote cases are looked up by deterministic case key before create.

**What happens when GHL is down?** A failed customer effect persists as RETRY with attempt/error/next-attempt state. Scheduled reconciliation resumes without changing the technical incident. A missing local acknowledgement is repaired by finding the existing remote case.

**What happens when NIM is down?** The assessment becomes unavailable; incident/evidence remain valid. Independent policy can still offer a proposal, but approval is always required. The provider is not on an autonomous remediation path.

**How are stale or contradictory replies handled?** A tag needs supporting inbound evidence newer than recovery. The latest relevant reply governs. Negative or uncertain text cannot support a positive marker, and conflicting tags are cleared conservatively. This is an English-only demo matcher, not a general language classifier.

**Why poll GHL feedback?** The cloud location cannot call localhost. Native workflow result tags plus local polling demonstrate the handoff without exposing local services. Production would use authenticated inbound delivery with replay protection and reconciliation.

**What changes in production?** Operator identity/access controls, authenticated event producers, managed runtime/database, secret management, observability, incident retention, deployment integration, stronger provider idempotency, and operational ownership. Existing controlled proofs do not establish distributed exactly-once behavior or production availability.
