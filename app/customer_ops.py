"""Small, retryable RelayCart→HighLevel customer-impact projection.

Technical incident state is authoritative locally. This module only mirrors it to
synthetic Service Cases in the isolated RelayCart Demo location.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone

import httpx

from app.db import get_connection

OBJECT = "custom_objects.relaycart_service_case"
ASSOCIATION_ID = "6abb11b64427829e84164de5"


def _request(client: httpx.Client, method: str, path: str, **kwargs) -> dict:
    response = client.request(method, path, **kwargs)
    # HighLevel's per-location burst budget is smaller than an 18-case fanout.
    time.sleep(0.7)
    if not response.is_success:
        raise RuntimeError(f"HighLevel {method} {path} returned HTTP {response.status_code}")
    result = response.json()
    if not isinstance(result, dict):
        raise RuntimeError("HighLevel returned a non-object response")
    return result


def enqueue() -> int:
    """One deterministic effect per subscribed customer and technical incident."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT i.incident_id, i.service, i.severity, i.state, i.summary,
                   i.opened_at, i.updated_at, i.recovered_at, i.revision,
                   c.slug AS customer_key, gc.contact_id
            FROM ir_incidents i
            JOIN services s ON s.service_key = i.service
            JOIN customer_service_subscriptions css ON css.service_id = s.id AND css.status = 'active'
            JOIN customers c ON c.id = css.customer_id
            JOIN ghl_contacts gc ON gc.customer_key = c.slug
            WHERE i.environment = 'production-demo' AND i.state <> 'RESOLVED'
            ORDER BY i.opened_at, c.slug
        """).fetchall()
        for row in rows:
            state = {
                "technical_status": row["state"], "severity": row["severity"],
                "impact_summary": row["summary"] or "RelayCart service incident",
                "revision": row["revision"],
                "updated_at": row["updated_at"].isoformat(),
                "recovered_at": row["recovered_at"].isoformat() if row["recovered_at"] else None,
            }
            conn.execute("""
                INSERT INTO ghl_effects(effect_id, incident_id, customer_key, effect_type, desired_state)
                VALUES (%s, %s, %s, 'service_case', %s)
                ON CONFLICT (effect_id) DO UPDATE
                SET desired_state=EXCLUDED.desired_state, status='PENDING', next_attempt_at=NOW(),
                    updated_at=NOW()
                WHERE ghl_effects.desired_state IS DISTINCT FROM EXCLUDED.desired_state
            """, (f"service-case:{row['incident_id']}:{row['customer_key']}",
                  row["incident_id"], row["customer_key"], json.dumps(state)))
    return len(rows)


def _properties(effect: dict) -> dict:
    desired = effect["desired_state"]
    incident_id, customer_key = effect["incident_id"], effect["customer_key"]
    properties = {
        "case_key": f"SC-{incident_id}-{customer_key}",
        "incident_id": incident_id,
        "customer_key": customer_key,
        "service": effect["service"],
        "severity": desired["severity"],
        "impact_summary": desired["impact_summary"][:1000],
        "technical_status": desired["technical_status"],
        "last_technical_update": desired["updated_at"][:10],
        "sync_revision": desired["revision"],
        "demo_record": "yes",
    }
    if desired["recovered_at"]:
        properties["recovery_verified_at"] = desired["recovered_at"][:10]
    return properties


def _find_case(client: httpx.Client, location: str, case_key: str) -> str | None:
    result = _request(client, "POST", f"/objects/{OBJECT}/records/search", json={
        "locationId": location, "page": 1, "pageLimit": 20,
        "query": case_key, "searchAfter": [],
    })
    records = [item for item in result.get("records", [])
               if item.get("properties", {}).get("case_key") == case_key]
    if len(records) > 1:
        raise RuntimeError(f"Duplicate HighLevel Service Case identity: {case_key}")
    return records[0]["id"] if records else None


def _ensure_relation(client: httpx.Client, location: str, contact_id: str, record_id: str) -> None:
    result = _request(client, "GET", f"/associations/relations/{contact_id}", params={
        "locationId": location, "skip": 0, "limit": 100,
    })
    relations = result.get("relations", [])
    if any(item.get("secondRecordId") == record_id and item.get("associationId") == ASSOCIATION_ID
           for item in relations):
        return
    _request(client, "POST", "/associations/relations", json={
        "locationId": location, "associationId": ASSOCIATION_ID,
        "firstRecordId": contact_id, "secondRecordId": record_id,
    })


def _process_effect(client: httpx.Client, location: str, effect: dict) -> str:
    properties = _properties(effect)
    case_key = properties["case_key"]
    record_id = effect["ghl_record_id"] or _find_case(client, location, case_key)
    if record_id is None:
        properties["customer_status"] = "AWAITING_RECOVERY"
        properties["affected_since"] = effect["opened_at"].date().isoformat()
        result = _request(client, "POST", f"/objects/{OBJECT}/records", json={
            "locationId": location, "properties": properties,
        })
        record_id = result["record"]["id"]
        # Persist the remote ID before the subsequent relation request can fail.
        with get_connection() as conn:
            conn.execute("UPDATE ghl_effects SET ghl_record_id=%s, updated_at=NOW() WHERE effect_id=%s",
                         (record_id, effect["effect_id"]))
    else:
        _request(client, "PUT", f"/objects/{OBJECT}/records/{record_id}",
                 params={"locationId": location}, json={"properties": properties})
    _ensure_relation(client, location, effect["contact_id"], record_id)
    return record_id


def _ensure_followup_task(client: httpx.Client, row: dict) -> str:
    """Create one visible, unassigned task when this isolated location has no staff."""
    title = f"RelayCart follow-up · {row['incident_id']}"
    path = f"/contacts/{row['contact_id']}/tasks"
    current = _request(client, "GET", path)
    matches = [task for task in current.get("tasks", []) if task.get("title") == title]
    if len(matches) > 1:
        raise RuntimeError("Duplicate RelayCart support tasks found")
    if matches:
        return matches[0]["id"]
    due = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    result = _request(client, "POST", path, json={
        "title": title,
        "body": (f"Synthetic RelayCart customer {row['customer_key']} reports checkout still failing "
                 f"after technical incident {row['incident_id']} was RECOVERED. "
                 f"Review Service Case {row['ghl_record_id']} for checkout-api context; investigate "
                 "the customer-specific problem. Do not reopen or remediate the technical incident automatically."),
        "dueDate": due, "completed": False,
    })
    return result["task"]["id"]


def sync(*, simulate_503: bool = False, limit: int = 3) -> dict:
    # The schedule and manual reconciliation may overlap. A transaction-scoped
    # advisory lock keeps both from creating the same remote case concurrently;
    # it is released automatically if the process dies.
    with get_connection() as guard:
        acquired = guard.execute("SELECT pg_try_advisory_xact_lock(731903001) AS acquired").fetchone()
        if not acquired["acquired"]:
            return {"affected": 0, "processed": 0, "succeeded": 0, "retry": 0,
                    "status": "already_running"}
        return _sync_locked(simulate_503=simulate_503, limit=limit)


def _sync_locked(*, simulate_503: bool, limit: int) -> dict:
    location = os.environ.get("GHL_LOCATION_ID", "")
    token = os.environ.get("GHL_LOCATION_TOKEN", "")
    if not location or not token:
        raise RuntimeError("GHL location credentials not configured")
    affected = enqueue()
    with get_connection() as conn:
        effects = conn.execute("""
            SELECT e.*, i.service, i.opened_at, gc.contact_id
            FROM ghl_effects e JOIN ir_incidents i ON i.incident_id=e.incident_id
            JOIN ghl_contacts gc ON gc.customer_key=e.customer_key AND gc.location_id=%s
            WHERE e.status IN ('PENDING','RETRY') AND e.next_attempt_at <= NOW()
            ORDER BY e.created_at, e.customer_key LIMIT %s
        """, (location, limit)).fetchall()
    succeeded = failed = 0
    with httpx.Client(base_url="https://services.leadconnectorhq.com", timeout=20,
                      trust_env=False, headers={"Authorization": "Bearer " + token,
                                                "Version": "v3", "Accept": "application/json"}) as client:
        for effect in effects:
            try:
                if simulate_503:
                    raise RuntimeError("Controlled HighLevel HTTP 503 fixture")
                record_id = _process_effect(client, location, effect)
                with get_connection() as conn:
                    conn.execute("""UPDATE ghl_effects SET status='SUCCEEDED', attempt_count=attempt_count+1,
                        ghl_record_id=%s, last_error=NULL, updated_at=NOW() WHERE effect_id=%s""",
                        (record_id, effect["effect_id"]))
                succeeded += 1
            except (RuntimeError, httpx.HTTPError, KeyError) as error:
                # No remote payload or token is persisted in this bounded error description.
                with get_connection() as conn:
                    conn.execute("""UPDATE ghl_effects SET status='RETRY', attempt_count=attempt_count+1,
                        next_attempt_at=NOW()+INTERVAL '15 seconds', last_error=%s, updated_at=NOW()
                        WHERE effect_id=%s""", (str(error)[:200], effect["effect_id"]))
                failed += 1
    return {"affected": affected, "processed": len(effects), "succeeded": succeeded, "retry": failed}


def poll_feedback() -> dict:
    """Reconcile native Conversation AI branch tags to their mapped Service Cases.

    The cloud GHL location cannot call a localhost n8n webhook. Tags are native
    workflow effects, and this bounded poll is the local return path. Technical
    incident state is read-only throughout.
    """
    location = os.environ.get("GHL_LOCATION_ID", "")
    token = os.environ.get("GHL_LOCATION_TOKEN", "")
    if not location or not token:
        raise RuntimeError("GHL location credentials not configured")
    with get_connection() as conn:
        rows = conn.execute("""SELECT e.incident_id,e.customer_key,e.ghl_record_id,
                   gc.contact_id,i.state
            FROM ghl_effects e JOIN ir_incidents i ON i.incident_id=e.incident_id
            JOIN ghl_contacts gc ON gc.customer_key=e.customer_key AND gc.location_id=%s
            WHERE e.status='SUCCEEDED' AND i.state='RECOVERED'
              AND i.opened_at=(SELECT max(opened_at) FROM ir_incidents
                               WHERE service=i.service AND environment=i.environment)
            ORDER BY e.customer_key""", (location,)).fetchall()
    if not rows:
        return {"eligible": 0, "observed": 0, "recorded": 0}
    observed = recorded = 0
    with httpx.Client(base_url="https://services.leadconnectorhq.com", timeout=20,
                      trust_env=False, headers={"Authorization": "Bearer " + token,
                                                "Version": "v3", "Accept": "application/json"}) as client:
        with get_connection() as conn:
            pending_tasks = conn.execute("""SELECT DISTINCT ON (f.incident_id,f.customer_key)
                f.incident_id,f.customer_key,f.ghl_record_id,gc.contact_id
                FROM ghl_customer_feedback f JOIN ghl_contacts gc ON gc.customer_key=f.customer_key
                WHERE f.incident_id=%s AND f.outcome='NEEDS_FOLLOW_UP'
                ORDER BY f.incident_id,f.customer_key,f.occurred_at DESC""",
                (rows[0]["incident_id"],)).fetchall()
        for row in pending_tasks:
            _ensure_followup_task(client, row)
        result = _request(client, "GET", "/contacts/", params={"locationId": location, "limit": 100})
        if result.get("meta", {}).get("nextPage"):
            raise RuntimeError("GHL contact list pagination required for feedback poll")
        contacts = {item["id"]: item for item in result.get("contacts", [])}
        for row in rows:
            contact = contacts.get(row["contact_id"])
            if not contact:
                continue
            tags = set(contact.get("tags") or [])
            outcome = ("NEEDS_FOLLOW_UP" if "relaycart-needs-follow-up" in tags else
                       "CONFIRMED_RESOLVED" if "relaycart-confirmed-resolved" in tags else None)
            if not outcome:
                continue
            observed += 1
            with get_connection() as conn:
                existing = conn.execute("""SELECT outcome FROM ghl_customer_feedback
                    WHERE incident_id=%s AND customer_key=%s ORDER BY occurred_at DESC LIMIT 1""",
                    (row["incident_id"], row["customer_key"])).fetchone()
            if not existing:
                if outcome == "NEEDS_FOLLOW_UP":
                    _ensure_followup_task(client, row)
                today = datetime.now(timezone.utc).date().isoformat()
                props = {"customer_status": outcome}
                if outcome == "CONFIRMED_RESOLVED":
                    props["customer_confirmed_at"] = today
                _request(client, "PUT", f"/objects/{OBJECT}/records/{row['ghl_record_id']}",
                         params={"locationId": location}, json={"properties": props})
                with get_connection() as conn:
                    conn.execute("""INSERT INTO ghl_customer_feedback
                        (incident_id,customer_key,ghl_record_id,outcome,occurred_at)
                        VALUES (%s,%s,%s,%s,NOW()) ON CONFLICT DO NOTHING""",
                        (row["incident_id"], row["customer_key"], row["ghl_record_id"], outcome))
                recorded += 1
            # Clear only our two transient outcome tags, so a later incident cannot
            # inherit stale branch outcomes. Keep the stable relaycart-demo marker.
            _request(client, "DELETE", f"/contacts/{row['contact_id']}/tags",
                     json={"tags": [tag for tag in tags if tag in
                                    ("relaycart-needs-follow-up", "relaycart-confirmed-resolved")]})
    return {"eligible": len(rows), "observed": observed, "recorded": recorded}
