# Five-minute interview demo

Use the prepared final state for the customer section. For a fresh full run, follow the runbook and allow several minutes for GHL batching before the interview. Keep the proof matrix open; do not run destructive tests during the presentation.

| Time | Action | Say / point out |
| --- | --- | --- |
| 0:00 | Open RelayCart at `http://127.0.0.1:8001` | “This is synthetic checkout software. Deployment, product recovery, and customer resolution are separate facts.” |
| 0:30 | Show healthy `v1.8.1`; create checkout and open the order | “I verify a transaction and its persisted order, not just a health endpoint.” |
| 0:50 | For a fresh run, deploy `v1.8.2` from the dashboard | “The deployment completes. The resulting application can still be broken.” |
| 1:10 | Probe health and attempt checkout; show separate log events | “Deployment, health, and checkout are independently observed.” |
| 1:30 | Show incident panel and IR 01 in n8n | “Postgres stores distinct signals in one incident; severity is deterministic.” |
| 2:00 | Open IR 02 and the assessment | “NIM receives bounded evidence. Output is validated. Provider failure leaves policy and approval intact.” |
| 2:30 | Open `/webhook/phase2/approval/pending` on n8n | “This approval authorizes only `v1.8.2 → v1.8.1`, once, before expiry.” |
| 3:00 | Approve; show four persisted verification checks | “HTTP 200 from rollback is insufficient. All business checks must pass.” |
| 3:30 | Show GHL 01 and the 18 associated Service Cases | “Only checkout subscribers receive cases; Green Dental is unaffected. Cross-platform orchestration is in n8n.” |
| 4:00 | Show prepared Acme conversation and case | “Acme explicitly confirms that checkout works.” |
| 4:20 | Show prepared Ocean conversation, case, and one task | “Ocean still has an issue. The global incident stays recovered; support owns this customer's follow-up.” |
| 4:40 | Show GHL 02 and customer dashboard | “Silence, ambiguous replies, and stale result tags cannot falsely close cases.” |
| 5:00 | Open Phase 4 matrix; highlight stale approval and false recovery | “A newer release blocks an old rollback. Healthy service plus broken checkout stays NEEDS_ATTENTION.” |
| 5:30 | End on architecture diagram | “The workflows expose the process; durable state proves the boundaries.” |

For a prepared demo, use the historical degraded screenshot and the recorded technical proofs instead of resetting the final customer state. State explicitly which view is historical. Never display approval tokens, credential editors, browser storage, or private configuration.

Fresh synthetic replies, after all 18 cases have synchronized:

```sh
docker compose exec -T api python scripts/phase3-live-chat-test acme-bikes working
docker compose exec -T api python scripts/phase3-live-chat-test ocean-apparel-02 broken
docker compose exec -T api python scripts/phase3-verify-ghl
```

The native Conversation AI and n8n schedules are asynchronous. Pre-stage this segment; a five-minute demo should not depend on provider latency or six GHL batches completing on cue.
