"""RelayCart product contracts consumed by the Phase 2 n8n workflows."""

import os

import httpx
import pytest

from psycopg.types.json import Jsonb

from app.db import get_connection


BASE_URL = os.getenv("RELAYCART_BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture
def api():
    with httpx.Client(base_url=BASE_URL, timeout=15) as client:
        reset = client.post("/demo/reset")
        assert reset.status_code == 200, reset.text
        yield client
        cleanup = client.post("/demo/reset")
        assert cleanup.status_code == 200, cleanup.text


def checkout(client):
    return client.post(
        "/checkout",
        json={"customer_slug": "acme-bikes", "amount": "12.00", "currency": "USD"},
    )


def test_neutral_release_is_healthy_and_supports_real_checkout(api):
    deployed = api.post("/deploy", json={"version": "v1.8.3"})
    assert deployed.status_code == 200, deployed.text
    assert deployed.json()["outcome"] == "completed"
    assert api.get("/version").json()["version"] == "v1.8.3"
    assert api.get("/health").json() == {
        "status": "healthy",
        "version": "v1.8.3",
        "service": "checkout-api",
    }

    created = checkout(api)
    assert created.status_code == 201, created.text
    order_id = created.json()["order_id"]
    assert api.get(f"/orders/{order_id}").status_code == 200


def test_rollback_is_bound_to_approved_source_and_target(api):
    assert api.post("/deploy", json={"version": "v1.8.2"}).status_code == 200
    result = api.post(
        "/rollback",
        json={
            "expected_source_version": "v1.8.2",
            "target_version": "v1.8.1",
            "request_id": "remediation-test-001",
        },
    )
    assert result.status_code == 200, result.text
    assert result.json() == {
        "version": "v1.8.1",
        "source_version": "v1.8.2",
        "target_version": "v1.8.1",
        "outcome": "succeeded",
        "request_id": "remediation-test-001",
    }
    assert "health" not in result.json()
    assert api.get("/version").json()["version"] == "v1.8.1"
    rollback_event = next(
        event for event in api.get("/logs").json()["events"]
        if event["event_type"] == "deployment.rollback"
    )
    assert rollback_event["details"]["request_id"] == "remediation-test-001"
    assert rollback_event["details"]["source_version"] == "v1.8.2"
    assert rollback_event["details"]["target_version"] == "v1.8.1"


def test_rollback_request_id_replays_once_and_rejects_different_binding(api):
    assert api.post("/deploy", json={"version": "v1.8.2"}).status_code == 200
    bound_request = {
        "expected_source_version": "v1.8.2",
        "target_version": "v1.8.1",
        "request_id": "remediation-replay-001",
    }
    first = api.post("/rollback", json=bound_request)
    assert first.status_code == 200, first.text
    event_count = len(api.get("/logs").json()["events"])

    replay = api.post("/rollback", json=bound_request)
    assert replay.status_code == 200, replay.text
    assert replay.json() == first.json()
    assert len(api.get("/logs").json()["events"]) == event_count

    conflicting = api.post(
        "/rollback",
        json={**bound_request, "expected_source_version": "v1.8.3"},
    )
    assert conflicting.status_code == 409
    assert api.get("/version").json()["version"] == "v1.8.1"


def test_stale_rollback_does_not_change_newer_release(api):
    assert api.post("/deploy", json={"version": "v1.8.2"}).status_code == 200
    assert api.post("/deploy", json={"version": "v1.8.3"}).status_code == 200
    before = len(api.get("/logs").json()["events"])

    stale = api.post(
        "/rollback",
        json={"expected_source_version": "v1.8.2", "target_version": "v1.8.1"},
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["detail"] == {
        "code": "stale_source_version",
        "expected_source_version": "v1.8.2",
        "current_version": "v1.8.3",
    }
    assert api.get("/version").json()["version"] == "v1.8.3"
    assert api.get("/health").json()["status"] == "healthy"
    assert len(api.get("/logs").json()["events"]) == before


def test_rollback_requires_exact_fields_for_automation_and_keeps_manual_ui_compatibility(api):
    assert api.post("/rollback", json={}).status_code == 422
    assert api.post("/deploy", json={"version": "v1.8.2"}).status_code == 200
    manual = api.post("/rollback")
    assert manual.status_code == 200, manual.text
    assert manual.json()["target_version"] == "v1.8.1"
    assert api.get("/version").json()["version"] == "v1.8.1"


def test_business_failure_fixture_keeps_health_green_and_reset_clears_it(api):
    assert api.get("/health").json()["status"] == "healthy"
    enabled = api.post("/demo/checkout-fault", json={"enabled": True})
    assert enabled.status_code == 200
    assert enabled.json() == {"checkout_failure_enabled": True}

    assert api.get("/health").json()["status"] == "healthy"
    failed_checkout = checkout(api)
    assert failed_checkout.status_code == 503
    failure = next(
        event for event in api.get("/logs").json()["events"]
        if event["event_type"] == "checkout.failed"
    )
    assert failure["details"]["failure_mode"] == "synthetic_business_failure"
    assert failure["details"]["reason"] == "synthetic business transaction failure"

    assert api.post("/demo/reset").status_code == 200
    assert api.get("/health").json()["status"] == "healthy"
    assert checkout(api).status_code == 201


def test_active_incident_projection_is_read_only_and_handles_empty_state(api):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO ir_incidents(incident_id,service,environment,severity,state,correlation_key,"
            "summary,current_version,healthy_version) "
            "VALUES ('INC-PHASE2-READONLY-TEST','checkout-api','production-demo','SEV-2',"
            "'INVESTIGATING','deployment-test','Synthetic incident projection fixture','v1.8.2','v1.8.1')"
        )
        conn.execute(
            "INSERT INTO ir_events(event_id,source,event_type,service,environment,occurred_at,"
            "correlation_hint,metadata) VALUES ('evt-readonly-test','relaycart','health.failed',"
            "'checkout-api','production-demo',NOW(),'deployment-test',%s)",
            (Jsonb({"version": "v1.8.2"}),),
        )
        conn.execute(
            "INSERT INTO ir_incident_events(incident_id,event_id,relationship) "
            "VALUES ('INC-PHASE2-READONLY-TEST','evt-readonly-test','trigger')"
        )
        conn.execute(
            "INSERT INTO ir_evidence(incident_id,evidence_key,kind,summary,source_event_id,payload) "
            "VALUES ('INC-PHASE2-READONLY-TEST','E1','event','Health check failed',"
            "'evt-readonly-test',%s)",
            (Jsonb({"status": "unhealthy"}),),
        )
        conn.execute(
            "INSERT INTO ir_assessments(incident_id,revision,status,provider,model,assessment) "
            "VALUES ('INC-PHASE2-READONLY-TEST',1,'valid','nvidia-nim','test-model',%s)",
            (Jsonb({"hypotheses": [{"summary": "Recent release may be related"}]}),),
        )
        conn.execute(
            "INSERT INTO ir_proposals(proposal_id,incident_id,revision,action_type,source_version,"
            "target_version,reason,status) VALUES ('RMP-PHASE2-READONLY-TEST',"
            "'INC-PHASE2-READONLY-TEST',1,'rollback','v1.8.2','v1.8.1',"
            "'Restore the last healthy release','PROPOSED')"
        )

    response = api.get("/incidents/latest")
    assert response.status_code == 200, response.text
    incident = response.json()["incident"]
    assert incident["incident_id"] == "INC-PHASE2-READONLY-TEST"
    assert incident["is_active"] is True
    assert incident["current_version"] == "v1.8.2"
    assert incident["healthy_version"] == "v1.8.1"
    assert incident["timeline"][0]["event_type"] == "health.failed"
    assert incident["evidence"][0]["evidence_key"] == "E1"
    assert incident["assessment"]["status"] == "valid"
    assert incident["proposal"]["target_version"] == "v1.8.1"
    assert "approval" not in incident["proposal"]

    with get_connection() as conn:
        conn.execute(
            "UPDATE ir_incidents SET state='RECOVERED',updated_at=NOW() "
            "WHERE incident_id='INC-PHASE2-READONLY-TEST'"
        )
    recovered = api.get("/incidents/latest").json()["incident"]
    assert recovered["state"] == "RECOVERED"
    assert recovered["is_active"] is False
