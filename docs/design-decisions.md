# Design decisions

| Decision | Reason / tradeoff |
| --- | --- |
| Many signals, one incident | Deployment completion supplies context; health and checkout establish impact. Events remain separately inspectable. One nonterminal incident per service/environment prevents competing response paths. |
| Deterministic severity | SEV-1/2/3 derives from explicit signals; model prose cannot silently change incident priority. |
| Advisory AI | Bounded evidence, strict schema/enums/reference validation, no tools. Unavailable/invalid advice is retained as a status, not treated as authority. |
| Exact human approval | Single-use, expiring source/target approval limits what an operator authorized. Local UI intentionally omits production IAM. |
| Stale-action invalidation | A newer release makes the approved source obsolete. Check before execution and again at the API mutation boundary. |
| Business verification | Release, health, checkout creation, and order read-back must all pass. A rollback response proves only the operation's result. |
| Technical/customer separation | A global recovery cannot close a merchant-specific problem. GHL confirmation/follow-up never automatically rolls back the product. |
| n8n orchestration | Policy, iteration, HTTP calls, retry/error branches, and durable transitions remain reviewable in the workflow graphs. Python supplies the deterministic world and narrow audit tools. |
| PostgreSQL durability | Unique keys, atomic claims with leases, effect state, and bound requests survive duplicates and execution restarts. Cross-platform HTTP writes are still not a distributed transaction. |
| GHL customer operations | Real contacts, Service Cases, associations, native workflows, Conversation AI, and tasks demonstrate the business handoff with synthetic data. |
| Local polling | Cloud GHL cannot reach localhost. Polling adds latency but keeps the demonstration local; authenticated webhooks would suit a hosted deployment. |
| Conservative reply handling | A native outcome tag needs a newer matching inbound reply. Latest-reply/negation checks prevent known false closures; English-only patterns leave uncertain cases pending. |
| Safe import exports | Inactive/omitted active state avoids starting schedules before credentials and instance-specific IDs are rebound. Runtime activation is audited separately. |

Phase 4 repaired two feedback boundary defects: positive keyword matching accepted negation, and a duplicate feedback insert returned no item to the tag-cleanup node. The repairs preserve the existing graph and are tested against its actual node code and live replay.
