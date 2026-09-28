# Phase 2 demo

This is the tested local technical incident-response walkthrough. The NIM step depends on provider availability; an unavailable or invalid AI response is recorded but does not grant action authority. See [Phase 2 verification](phase-2-verification.md) for actual evidence.

## Prepare

Start RelayCart and connect the existing n8n instance:

```sh
docker compose up --build -d
./scripts/connect-n8n
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U relaycart -d relaycart < n8n/schema.sql
```

Open the RelayCart operations console at <http://127.0.0.1:8001> and reset demo state. The baseline should be `v1.8.1`, healthy, with successful checkout and order readback. Inspect the active incident panel only after checking that the incident schema is installed.

## Healthy deployment and incident recovery

1. Deploy `v1.8.2`. The operation records `deployment.completed`.
2. Let a health probe run and issue a checkout. They independently produce `health.failed` and `checkout.failed`.
3. Confirm event intake deduplicates the signals and correlates them into one checkout-api incident.
4. Inspect the persisted evidence and NVIDIA NIM assessment. The assessment is advice, not action authority.
5. Open the local approval page at <http://127.0.0.1:5678/webhook/phase2/approval/pending>. Review the exact rollback proposal and explicitly choose **Approve exact rollback** or **Reject**. Opening or refreshing the page has no side effect. Rejection or expiry must not run rollback.
6. Confirm the workflow re-reads the live release before using approval, performs the version-bound rollback, and checks release version, health, checkout, and order readback.
7. Confirm n8n moves the incident to `RECOVERED` only after every required check succeeds. Allow roughly a minute for scheduled intake/investigation before the approval appears.

The approval page is a loopback-only demo surface, not production operator authentication. Do not expose it publicly.

## Stale approval scenario

1. Recreate the `v1.8.2` incident and capture its proposal for `v1.8.2 → v1.8.1`.
2. Before executing the approval, deploy the supported neutral release `v1.8.3`.
3. Submit the earlier approval.
4. Confirm the remediation attempt is blocked as stale, the current version remains `v1.8.3`, and the incident does not become recovered.

The tested outcome was HTTP 409 `stale_approval_blocked`, a visible `v1.8.2`/`v1.8.3` mismatch, and no rollback side effect. Submit the old approval promptly after deploying `v1.8.3`; a later intake cycle may instead invalidate the old proposal before it can be submitted, which is also safe.

## Healthy health check with failed business transaction

The `/demo/checkout-fault` fixture can make checkout fail while `/health` stays healthy. Enable it before approving a `v1.8.2 → v1.8.1` rollback: the rollback succeeds and health becomes green, but checkout and order read-back fail, so n8n ends in `NEEDS_ATTENTION`, not `RECOVERED`. Reset clears the fixture.
