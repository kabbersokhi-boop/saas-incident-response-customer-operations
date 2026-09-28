# RelayCart incident response demo

RelayCart is a local, synthetic SaaS operations demo. It illustrates a healthy checkout, a successful deployment operation, an independent application health failure on v1.8.2, failed checkout evidence, manual rollback, and order readback after recovery. Deployment completion, application health, and business transaction success are distinct facts. It does not connect to real stores, customers, payment providers, or production systems. Incidents are not detected automatically and no customer messages are sent.

Dashboard evidence: [healthy](docs/evidence/healthy.png) · [degraded](docs/evidence/degraded.png) · [recovered](docs/evidence/recovered.png).

## Start

Requirements: Docker Engine and the Docker Compose plugin.

```sh
cp .env.example .env
docker compose up --build -d
docker compose ps
```

The API and UI are served together at <http://127.0.0.1:8001>. The API container listens on port 8000; host port 8001 is used because localhost:8000 is already occupied. PostgreSQL is only reachable by other Compose services and is not published on the host. The demo uses local-only credentials from `.env.example`; do not reuse them elsewhere.

## Demo: healthy → deploy → detect → rollback

1. Open the dashboard at <http://127.0.0.1:8001>. Run the checkout canary and confirm the order can be read back.
2. Deploy v1.8.2 from the dashboard. The deployment operation completes. Then confirm `/health` independently reports the unhealthy application state, `docker compose ps` shows the API as unhealthy, a new checkout fails, and `/logs` contains separate `deployment.completed`, `health.failed`, and `checkout.failed` events.
3. Roll back manually from the dashboard. Confirm the API returns to healthy, run another checkout, and verify its order readback.
4. Select **Reset demo state** in the dashboard (or call `POST /demo/reset`) to restore the repeatable baseline.

The demo changes synthetic application state only. No real incident actions or customer messages are performed.

## Test and verify

Run the project's documented verification script:

```sh
./scripts/verify
```

It runs the black-box test suite inside the API container. To invoke pytest directly:

```sh
docker compose exec -T api pytest -q
```

Check the container health and API response:

```sh
docker compose ps
curl -fsS http://127.0.0.1:8001/health
```

Docker Compose health checks cover PostgreSQL readiness and API health, including the application's reported healthy state. The API waits for PostgreSQL's healthy state before starting. The API container becomes unhealthy during the simulated v1.8.2 failure and healthy again after rollback. The deploy endpoint reports only whether the release operation completed; it does not certify application health. Repeated health polls create at most one `health.failed` event for a deployment.

## Stop and reset

Stop containers while keeping demo data:

```sh
docker compose down
```

For a clean database reset, stop the stack and delete the local database volume:

```sh
docker compose down -v
```

The volume removal is destructive to this demo's stored data. Use it only when you want a clean local reset.

## Boundaries and roadmap

This Phase 1 build is a single-machine demo. It is not production-ready and has no real customer data, authentication, external notifications, payment integrations, or production incident automation. Keep `.env` local; it is ignored by Git. n8n and GoHighLevel are outside this demo and are not modified or required.

Roadmap: Phase 2 adds n8n technical incident automation; Phase 3 adds GoHighLevel (GHL) customer operations. Neither phase is implemented here: n8n and GHL are not connected, and no automation or customer operations run from this demo.

See [architecture](docs/architecture.md), [business scenario](docs/business-scenario.md), and [Phase 1 verification](docs/phase-1-verification.md).
