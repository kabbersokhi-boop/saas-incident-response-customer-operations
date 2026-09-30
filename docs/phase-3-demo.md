# Phase 3 reproduction

Prerequisites: local Compose services, connected Phase 2 n8n, published RelayCart workflows in the isolated HighLevel location, and ignored `.env` values for the location ID and location-scoped token. The local token must include contacts, custom-object records, associations, conversations/messages, and task access. Never commit `.env` or send real customer messages.

1. Verify the Phase 2 baseline: `./scripts/verify-phase2`. This resets local demo state.
2. Run `docker compose exec -T api python scripts/phase3-signature`. This resets to healthy `v1.8.1`, proves a checkout, deploys defective `v1.8.2`, waits for one correlated incident and 18 GHL cases, approves the existing Phase 2 rollback, and waits for all 18 cases to show `RECOVERED`.
3. In GHL, inspect Acme Bikes' associated Service Case and the three published RelayCart workflows. Green Dental must have no case for that incident.
4. Use only synthetic Live Chat conversations and HighLevel's inbound Live Chat test API: `docker compose exec -T api python scripts/phase3-live-chat-test acme-bikes working` and `docker compose exec -T api python scripts/phase3-live-chat-test ocean-apparel-02 broken`. These commands require the current incident to be technically recovered and both cases synchronized. The native Conversation AI action must execute and route each reply; allow the 60-second `GHL 02 — Customer Recovery Feedback` schedule to reconcile them.
5. Inspect GHL cases and the local dashboard. The same technical incident is `RECOVERED`; Acme's case is `CONFIRMED_RESOLVED`; Ocean's is `NEEDS_FOLLOW_UP` with one unassigned support task; Green Dental is `NOT AFFECTED`.

For an API-only, scoped outcome audit, run `docker compose exec -T api python scripts/phase3-verify-ghl`. Re-run `curl -X POST http://localhost:5678/webhook/relaycart/customer-impact/sync` to prove no duplicate cases. The dashboard is <http://127.0.0.1:8001>.

Live Chat widget browser pre-chat submission encountered a Cloudflare Turnstile challenge in headless automation. The tested GHL mechanism creates the synthetic conversation and inbound `Live_Chat` message through the documented Conversations API, then runs the actual published Conversation AI workflow. It sends no paid or real outbound message. This is test transport, not an assertion that a public widget passed Turnstile.
