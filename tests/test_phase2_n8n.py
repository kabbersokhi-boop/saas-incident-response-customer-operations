"""Black-box checks against the live local n8n event-intake webhook."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html.parser import HTMLParser
import os
import time
from uuid import uuid4

import httpx
import pytest
from psycopg.types.json import Jsonb

from app.db import get_connection


N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://n8n:5678")
EVENT_WEBHOOK = f"{N8N_BASE_URL}/webhook/ir/events"
APPROVAL_PAGE = f"{N8N_BASE_URL}/webhook/phase2/approval/pending"
APPROVAL_DECISION = f"{N8N_BASE_URL}/webhook/phase2/approval/decision"
SERVICE = "checkout-api"


@pytest.fixture
def run_scope():
    """Give each run private rows, then remove only the rows it created."""
    run_id = uuid4().hex
    prefix = f"phase2-it-{run_id}-"
    environment = f"phase2-test-{run_id}"
    try:
        yield {"run_id": run_id, "prefix": prefix, "environment": environment}
    finally:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM ir_incidents WHERE service=%s AND environment=%s",
                (SERVICE, environment),
            )
            conn.execute("DELETE FROM ir_events WHERE event_id LIKE %s", (f"{prefix}%",))


@pytest.fixture
def release_scope():
    """Preserve release/fault state around approval tests; never reset shared data."""
    client = httpx.Client(
        base_url=os.getenv("RELAYCART_BASE_URL", "http://127.0.0.1:8000"),
        timeout=20,
    )
    original_version = current_version(client)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM config WHERE config_key='demo_checkout_fault'"
        ).fetchone()
    original_fault = bool(row and row["value"].get("enabled"))
    try:
        yield {"client": client, "version": original_version, "fault": original_fault}
    finally:
        client.post("/demo/checkout-fault", json={"enabled": original_fault})
        if current_version(client) != original_version:
            deploy(client, original_version)
        client.close()


@pytest.fixture
def signature_scope():
    """Own the real production-demo signature fixture for one end-to-end test."""
    client = httpx.Client(
        base_url=os.getenv("RELAYCART_BASE_URL", "http://127.0.0.1:8000"),
        timeout=20,
    )
    assert client.post("/demo/reset").status_code == 200
    try:
        yield client
    finally:
        assert client.post("/demo/reset").status_code == 200
        client.close()


def production_proposal(client, *, business_fault=False):
    """Create a real correlated incident; the approval token stays in memory."""
    deploy(client, "v1.8.2")
    assert client.get("/health").json()["status"] == "unhealthy"
    failed = client.post(
        "/checkout",
        json={"customer_slug": "acme-bikes", "amount": "12.00", "currency": "USD"},
    )
    assert failed.status_code == 503
    if business_fault:
        assert client.post("/demo/checkout-fault", json={"enabled": True}).status_code == 200
    deadline = time.monotonic() + 100
    while time.monotonic() < deadline:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT i.incident_id,p.proposal_id,p.source_version,p.target_version,"
                "a.approval_id,ass.status AS assessment_status "
                "FROM ir_incidents i JOIN ir_proposals p USING(incident_id) "
                "JOIN ir_approvals a USING(proposal_id) "
                "JOIN ir_assessments ass ON ass.incident_id=i.incident_id "
                "AND ass.revision=i.revision "
                "WHERE i.environment='production-demo' AND i.service='checkout-api' "
                "AND i.state='WAITING_FOR_APPROVAL' AND p.status='PROPOSED' "
                "AND a.status='PENDING' ORDER BY i.opened_at DESC LIMIT 1"
            ).fetchone()
        if row:
            form = pending_form(row["proposal_id"])
            form["proposal_revision"] = int(form["proposal_revision"])
            return row, form
        time.sleep(0.5)
    pytest.fail("Production-demo incident did not reach WAITING_FOR_APPROVAL.")


def event(scope, event_type, suffix, *, occurred_at=None, severity_hint=None, version="v1.8.2"):
    now = occurred_at or datetime.now(timezone.utc)
    return {
        "event_id": f"{scope['prefix']}{suffix}",
        "source": "relaycart",
        "event_type": event_type,
        "service": SERVICE,
        "environment": scope["environment"],
        "occurred_at": now.isoformat(),
        "correlation_hint": f"deployment-{scope['run_id']}",
        "severity_hint": severity_hint,
        "metadata": {
            "version": version,
            "reason": "Synthetic Phase 2 integration fixture",
            "correlation_id": f"deployment-{scope['run_id']}",
            "environment": scope["environment"],
        },
    }


def post_event(payload):
    with httpx.Client(timeout=30) as client:
        return client.post(EVENT_WEBHOOK, json=payload)


def db_count(query, params):
    with get_connection() as conn:
        return conn.execute(query, params).fetchone()["count"]


class ApprovalForms(HTMLParser):
    """Extract hidden fields in memory; never include tokens in assertion text."""

    def __init__(self):
        super().__init__()
        self.forms = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "form" and "decision" in attributes.get("class", "").split():
            self.current = {}
        elif tag == "input" and self.current is not None:
            name = attributes.get("name")
            if name:
                self.current[name] = attributes.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form" and self.current is not None:
            self.forms.append(self.current)
            self.current = None


def create_approval_fixture(scope, *, expires_in=timedelta(minutes=10), source="v1.8.2", target="v1.8.1"):
    """Insert a synthetic, isolated approval. The bearer token stays in memory."""
    delivery_token = uuid4()
    token_hash = sha256(str(delivery_token).encode("utf-8")).hexdigest()
    with get_connection() as conn:
        incident = conn.execute(
            "INSERT INTO ir_incidents(service,environment,severity,state,correlation_key,"
            "latest_event_at,current_version,healthy_version,summary) "
            "VALUES (%s,%s,'SEV-2','WAITING_FOR_APPROVAL',%s,NOW(),%s,%s,%s) "
            "RETURNING incident_id",
            (
                SERVICE,
                scope["environment"],
                scope["run_id"],
                source,
                target,
                "Isolated synthetic approval integration test",
            ),
        ).fetchone()
        proposal = conn.execute(
            "INSERT INTO ir_proposals(incident_id,revision,action_type,source_version,"
            "target_version,reason,evidence_refs,status,expires_at) "
            "VALUES (%s,1,'rollback',%s,%s,%s,%s,'PROPOSED',NOW()+%s) "
            "RETURNING proposal_id,revision",
            (
                incident["incident_id"],
                source,
                target,
                "Isolated synthetic approval integration test",
                Jsonb(["E-TEST"]),
                expires_in,
            ),
        ).fetchone()
        approval = conn.execute(
            "INSERT INTO ir_approvals(proposal_id,proposal_revision,action_type,source_version,"
            "target_version,delivery_token,token_hash,status,expires_at) "
            "VALUES (%s,%s,'rollback',%s,%s,%s,%s,'PENDING',NOW()+%s) "
            "RETURNING approval_id",
            (
                proposal["proposal_id"],
                proposal["revision"],
                source,
                target,
                delivery_token,
                token_hash,
                expires_in,
            ),
        ).fetchone()
    return {
        "incident_id": incident["incident_id"],
        "proposal_id": proposal["proposal_id"],
        "proposal_revision": proposal["revision"],
        "approval_id": approval["approval_id"],
        "action_type": "rollback",
        "source_version": source,
        "target_version": target,
        "_token": str(delivery_token),
    }


def pending_form(proposal_id):
    with httpx.Client(timeout=15) as client:
        response = client.get(APPROVAL_PAGE)
    assert response.status_code == 200
    parser = ApprovalForms()
    parser.feed(response.text)
    for form in parser.forms:
        if form.get("proposal_id") == proposal_id:
            return form
    pytest.fail("Approval page did not render the expected current proposal.")


def post_decision(payload, decision):
    # The caller holds this body only in memory. Never log it: it contains a token.
    request = {key: value for key, value in payload.items() if not key.startswith("_")}
    request["decision"] = decision
    with httpx.Client(timeout=120) as client:
        return client.post(APPROVAL_DECISION, json=request)


def approval_state(approval_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT a.status AS approval_status,a.decision,p.status AS proposal_status,"
            "i.state AS incident_state FROM ir_approvals a "
            "JOIN ir_proposals p USING(proposal_id) JOIN ir_incidents i USING(incident_id) "
            "WHERE a.approval_id=%s",
            (approval_id,),
        ).fetchone()


def current_version(client):
    response = client.get("/version")
    assert response.status_code == 200
    return response.json()["version"]


def deploy(client, version):
    response = client.post("/deploy", json={"version": version})
    assert response.status_code == 200


def wait_for_attempt(approval_id, timeout=40):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with get_connection() as conn:
            attempt = conn.execute(
                "SELECT attempt_id,result,source_version,target_version,http_status,observed_version "
                "FROM ir_remediation_attempts WHERE approval_id=%s ORDER BY attempt_id DESC LIMIT 1",
                (approval_id,),
            ).fetchone()
        if attempt:
            return attempt
        time.sleep(0.5)
    pytest.fail("No remediation attempt was persisted before the timeout.")


def verification_rows(attempt_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT check_name,expected,observed,passed FROM ir_verification_checks "
            "WHERE attempt_id=%s ORDER BY check_name",
            (attempt_id,),
        ).fetchall()


def test_event_contract_rejects_invalid_and_concurrent_duplicates_are_idempotent(run_scope):
    invalid = event(run_scope, "health.failed", "invalid", severity_hint="SEV-4")
    invalid_response = post_event(invalid)
    assert invalid_response.status_code == 200, invalid_response.text
    assert invalid_response.json()["status"] == "invalid"

    duplicate_fixture = event(run_scope, "manual.test", "concurrent")
    with ThreadPoolExecutor(max_workers=20) as pool:
        responses = list(pool.map(lambda _: post_event(duplicate_fixture), range(20)))

    assert all(response.status_code == 200 for response in responses)
    statuses = [response.json()["status"] for response in responses]
    assert statuses.count("accepted") == 1
    assert statuses.count("duplicate") == 19
    assert db_count(
        "SELECT count(*) AS count FROM ir_events WHERE event_id=%s",
        (duplicate_fixture["event_id"],),
    ) == 1
    assert db_count(
        "SELECT count(*) AS count FROM ir_incident_events WHERE event_id=%s",
        (duplicate_fixture["event_id"],),
    ) == 0
    assert db_count(
        "SELECT count(*) AS count FROM ir_events WHERE event_id=%s",
        (invalid["event_id"],),
    ) == 0


def test_deployment_health_and_checkout_correlate_and_project_one_incident(run_scope):
    origin = datetime.now(timezone.utc)
    previous_deployment = event(
        run_scope, "deployment.completed", "previous-deployment", occurred_at=origin,
        version="v1.8.1",
    )
    deployment = event(
        run_scope, "deployment.completed", "deployment", occurred_at=origin + timedelta(seconds=1),
        version="v1.8.2",
    )
    health = event(
        run_scope, "health.failed", "health", occurred_at=origin + timedelta(seconds=3)
    )
    checkout = event(
        run_scope, "checkout.failed", "checkout", occurred_at=origin + timedelta(seconds=5)
    )

    previous_response = post_event(previous_deployment)
    assert previous_response.status_code == 200, previous_response.text
    assert previous_response.json()["status"] == "accepted"

    deployment_response = post_event(deployment)
    assert deployment_response.status_code == 200, deployment_response.text
    assert deployment_response.json()["status"] == "accepted"

    health_response = post_event(health)
    assert health_response.status_code == 200, health_response.text
    incident_id = health_response.json()["incident_id"]
    assert incident_id

    checkout_response = post_event(checkout)
    assert checkout_response.status_code == 200, checkout_response.text
    assert checkout_response.json()["incident_id"] == incident_id

    with get_connection() as conn:
        incident = conn.execute(
            "SELECT severity,state,revision,current_version,healthy_version "
            "FROM ir_incidents WHERE incident_id=%s",
            (incident_id,),
        ).fetchone()
        linked = conn.execute(
            "SELECT e.event_id,e.event_type,ie.relationship "
            "FROM ir_incident_events ie JOIN ir_events e USING(event_id) "
            "WHERE ie.incident_id=%s ORDER BY e.occurred_at,e.event_id",
            (incident_id,),
        ).fetchall()
        evidence_count = conn.execute(
            "SELECT count(*) AS count FROM ir_evidence WHERE incident_id=%s",
            (incident_id,),
        ).fetchone()["count"]

    assert incident["severity"] == "SEV-2"
    assert incident["state"] == "INVESTIGATING"
    assert incident["revision"] >= 2
    assert incident["current_version"] == "v1.8.2"
    assert incident["healthy_version"] == "v1.8.1"
    assert {row["event_id"] for row in linked} == {
        previous_deployment["event_id"], deployment["event_id"], health["event_id"], checkout["event_id"]
    }
    assert len(linked) == 4
    assert evidence_count == 4

    with httpx.Client(base_url=os.getenv("RELAYCART_BASE_URL", "http://127.0.0.1:8000"), timeout=10) as client:
        projection = client.get("/incidents/latest")
    assert projection.status_code == 200, projection.text
    projected = projection.json()
    assert projected["available"] is True
    incident_view = projected["incident"]
    assert incident_view["incident_id"]
    with get_connection() as conn:
        projected_row = conn.execute(
            "SELECT severity,state,service,environment FROM ir_incidents WHERE incident_id=%s",
            (incident_view["incident_id"],),
        ).fetchone()
        projected_event_ids = {
            row["event_id"] for row in conn.execute(
                "SELECT event_id FROM ir_incident_events WHERE incident_id=%s",
                (incident_view["incident_id"],),
            ).fetchall()
        }
    assert projected_row is not None
    assert incident_view["severity"] == projected_row["severity"]
    assert incident_view["state"] == projected_row["state"]
    assert incident_view["service"] == projected_row["service"]
    assert incident_view["environment"] == projected_row["environment"]
    assert {row["event_id"] for row in incident_view["timeline"]} == projected_event_ids


def test_approval_rejection_is_single_use_and_never_rolls_back(run_scope, release_scope):
    fixture = create_approval_fixture(run_scope)
    form = pending_form(fixture["proposal_id"])
    form["proposal_revision"] = int(form["proposal_revision"])
    before = current_version(release_scope["client"])

    rejected = post_decision(form, "reject")
    assert rejected.status_code == 200
    assert rejected.json().get("status") == "rejected"
    replayed = post_decision(form, "reject")
    assert replayed.status_code == 409
    assert replayed.json().get("status") == "invalid_or_already_used"

    state = approval_state(fixture["approval_id"])
    assert state["approval_status"] == "REJECTED"
    assert state["proposal_status"] == "REJECTED"
    assert state["incident_state"] == "NEEDS_ATTENTION"
    assert current_version(release_scope["client"]) == before
    assert db_count(
        "SELECT count(*) AS count FROM ir_remediation_attempts WHERE approval_id=%s",
        (fixture["approval_id"],),
    ) == 0


def test_expired_approval_escalates_without_rollback(run_scope, release_scope):
    fixture = create_approval_fixture(run_scope, expires_in=timedelta(seconds=-2))
    payload = {key: value for key, value in fixture.items() if key != "incident_id"}
    payload["token"] = payload.pop("_token")
    payload["decision"] = "approve"
    before = current_version(release_scope["client"])

    response = post_decision(payload, "approve")
    assert response.status_code in {409, 410}
    assert response.json().get("status") in {"expired", "invalid_or_already_used"}
    state = approval_state(fixture["approval_id"])
    assert state["approval_status"] == "EXPIRED"
    assert state["proposal_status"] == "EXPIRED"
    assert state["incident_state"] == "NEEDS_ATTENTION"
    assert current_version(release_scope["client"]) == before
    assert db_count(
        "SELECT count(*) AS count FROM ir_remediation_attempts WHERE approval_id=%s",
        (fixture["approval_id"],),
    ) == 0


def test_approval_for_old_release_is_blocked_after_new_deployment(signature_scope):
    client = signature_scope
    fixture, form = production_proposal(client)
    deploy(client, "v1.8.3")
    response = post_decision(form, "approve")
    assert response.status_code == 409
    result = response.json()
    assert result.get("status") == "stale_approval_blocked"
    assert result.get("approved_source_version") == "v1.8.2"
    assert result.get("current_version") == "v1.8.3"
    assert client.get("/version").json()["version"] == "v1.8.3"

    state = approval_state(fixture["approval_id"])
    assert state["approval_status"] == "CONSUMED"
    assert state["proposal_status"] == "STALE"
    assert state["incident_state"] == "NEEDS_ATTENTION"
    attempt = wait_for_attempt(fixture["approval_id"])
    assert attempt["result"] == "stale"
    assert db_count(
        "SELECT count(*) AS count FROM application_events WHERE event_type='deployment.rollback' "
        "AND details->>'request_id'=%s",
        (f"ir-approval-{fixture['approval_id']}-{form['proposal_revision']}",),
    ) == 0


def test_approved_rollback_recovers_only_after_all_four_checks(signature_scope):
    client = signature_scope
    fixture, form = production_proposal(client)
    response = post_decision(form, "approve")
    assert response.status_code == 200
    result = response.json()
    assert result.get("incident_state") == "RECOVERED"
    assert result.get("recovered") is True
    attempt = wait_for_attempt(fixture["approval_id"])
    assert attempt["result"] == "succeeded"
    checks = verification_rows(attempt["attempt_id"])
    assert {check["check_name"] for check in checks} == {
        "version", "health", "synthetic_checkout", "order_readback"
    }
    assert all(check["passed"] for check in checks)
    assert current_version(client) == "v1.8.1"
    health = client.get("/health").json()
    assert health["status"] == "healthy"
    assert health["version"] == "v1.8.1"


def test_successful_rollback_with_business_failure_does_not_recover(signature_scope):
    client = signature_scope
    fixture, form = production_proposal(client, business_fault=True)
    response = post_decision(form, "approve")
    assert response.status_code == 202
    assert response.json().get("incident_state") == "NEEDS_ATTENTION"
    assert current_version(client) == "v1.8.1"
    assert client.get("/health").json()["status"] == "healthy"
    attempt = wait_for_attempt(fixture["approval_id"])
    assert attempt["result"] == "succeeded"
    checks = {check["check_name"]: check["passed"] for check in verification_rows(attempt["attempt_id"])}
    assert checks == {
        "version": True,
        "health": True,
        "synthetic_checkout": False,
        "order_readback": False,
    }
    with get_connection() as conn:
        state = conn.execute(
            "SELECT state FROM ir_incidents WHERE incident_id=%s",
            (fixture["incident_id"],),
        ).fetchone()["state"]
    assert state == "NEEDS_ATTENTION"
