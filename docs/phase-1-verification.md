# Phase 1 verification

Start the stack with `docker compose up --build -d`, then inspect `docker compose ps`. Both `api` and `postgres` should report healthy. After deploying v1.8.2, `/health` returns JSON status `unhealthy` and Compose reports the API container unhealthy; after rollback both report healthy again. The following requests exercise a successful order, the bad release, failure evidence, rollback, readback after recovery, and reset:

```sh
curl -fsS http://127.0.0.1:8001/health
curl -fsS -X POST http://127.0.0.1:8001/checkout -H 'Content-Type: application/json' -d '{"customer_slug":"acme-bikes","amount":"129.99","currency":"USD"}'
curl -fsS http://127.0.0.1:8001/orders/ORDER_ID
curl -fsS -X POST http://127.0.0.1:8001/deploy -H 'Content-Type: application/json' -d '{"version":"v1.8.2"}'
curl -i http://127.0.0.1:8001/health
curl -i -X POST http://127.0.0.1:8001/checkout -H 'Content-Type: application/json' -d '{"customer_slug":"acme-bikes","amount":"129.99","currency":"USD"}'
curl -fsS http://127.0.0.1:8001/logs
curl -fsS -X POST http://127.0.0.1:8001/rollback
curl -fsS -X POST http://127.0.0.1:8001/checkout -H 'Content-Type: application/json' -d '{"customer_slug":"acme-bikes","amount":"129.99","currency":"USD"}'
curl -fsS http://127.0.0.1:8001/orders/RECOVERED_ORDER_ID
curl -fsS -X POST http://127.0.0.1:8001/demo/reset
```

Replace each order ID placeholder (`ORDER_ID` and `RECOVERED_ORDER_ID`) with the `order_id` returned by its checkout request. The failure request is expected to return HTTP 503. No incident detection or customer messaging is automated. The API health endpoint is <http://127.0.0.1:8001/health>.

Run `./scripts/verify` to execute the black-box checks inside the API container. The image includes the project tests and helper scripts. You can also run `docker compose exec -T api pytest -q` directly.

This procedure verifies only the local synthetic demo. It does not validate a production deployment or any external system. Do not report a check as passed unless it has actually been run.

## Observed Phase 1 run — 2026-09-28

- `docker compose up --build -d` started `api` and `postgres`; both reported healthy at the baseline.
- `./scripts/verify` reported **4 passed, 0 failed, 0 skipped** after the final build.
- A browser-driven run exercised the UI controls for healthy checkout, v1.8.2 deployment, failed checkout, rollback, recovered checkout/order readback, and reset without JavaScript errors. Screenshots: [healthy](evidence/healthy.png), [degraded](evidence/degraded.png), [recovered](evidence/recovered.png).
- While v1.8.2 was active, `/health` and `/demo/state` reported `unhealthy`, checkout returned HTTP 503, and `/logs` contained the correlated `checkout.failed` event with the missing `pricing_rules` evidence. Docker marked the API container unhealthy; it returned to healthy after rollback.
- PostgreSQL contained 30 customers, 30 plans, 51 customer-service links (18 checkout, 16 billing, 17 notification), 20 historical deployments, 10 historical incidents, and 20 historical service cases. No orphan service links were found.
- Reset restored v1.8.1, the 20-deployment baseline, and a clean demo order state.
