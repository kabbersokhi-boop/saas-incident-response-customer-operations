"""FastAPI service for the RelayCart incident response demo."""

from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb

from .db import get_connection, initialize_schema
from .seed import BAD_VERSION, CURRENT_VERSION, SERVICE_NAME, reset_demo, seed_baseline

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_schema()
    seed_baseline()
    yield


app = FastAPI(title="RelayCart Operations API", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR, check_dir=False), name="static")


class CheckoutRequest(BaseModel):
    customer_slug: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3, pattern="^[A-Za-z]{3}$")


class DeployRequest(BaseModel):
    version: str


def _checkout_probe(conn: Any) -> tuple[str, str, str | None]:
    """The health endpoint and checkout use the same real config compatibility check."""
    row = conn.execute(
        "SELECT ss.status, ss.version, c.value FROM service_state ss "
        "JOIN services s ON s.id=ss.service_id "
        "JOIN config c ON c.config_key='checkout' WHERE s.service_key='checkout-api'"
    ).fetchone()
    if not row:
        return "unhealthy", "unknown", "checkout service configuration is unavailable"
    status, version = row["status"], row["version"]
    if status != "healthy":
        return "unhealthy", version, "checkout service is marked unhealthy"
    if version == BAD_VERSION:
        try:
            # v1.8.2 now requires this field, but the persisted legacy JSON config
            # uses currency_rules. The resulting KeyError is the compatibility fault.
            row["value"]["pricing_rules"]["USD"]
        except (KeyError, TypeError):
            return "unhealthy", version, "required pricing_rules are missing from checkout configuration"
    return "healthy", version, None


def _event(
    conn: Any,
    *,
    level: str,
    event_type: str,
    service: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    safe_details = dict(details or {})
    safe_details.setdefault("environment", "demo")
    conn.execute(
        "INSERT INTO application_events(level,event_type,service,message,details) "
        "VALUES (%s,%s,%s,%s,%s)",
        (level.upper(), event_type, service, message, Jsonb(safe_details)),
    )


def _event_view(row: dict[str, Any]) -> dict[str, Any]:
    details = row.get("details") or {}
    return {
        "id": row["id"],
        "severity": str(row["level"]).lower(),
        "level": row["level"],
        "event_type": row["event_type"],
        "service": row["service"],
        "message": row["message"],
        "details": details,
        "environment": details.get("environment", "demo"),
        "correlation_id": details.get("correlation_id"),
        "version": details.get("version"),
        "timestamp": row["created_at"].isoformat(),
        "created_at": row["created_at"].isoformat(),
    }


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    try:
        with get_connection() as conn:
            status, version, _ = _checkout_probe(conn)
    except Exception:
        status, version = "unhealthy", "unknown"
    return {"status": status, "version": version, "service": SERVICE_NAME}


@app.get("/version")
def version() -> dict[str, str]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT ss.version FROM service_state ss JOIN services s ON s.id=ss.service_id "
            "WHERE s.service_key='checkout-api'"
        ).fetchone()
    return {"version": row["version"] if row else "unknown"}


@app.post("/checkout", status_code=201)
def checkout(request: CheckoutRequest) -> dict[str, Any]:
    if request.currency.upper() != "USD":
        raise HTTPException(status_code=400, detail="Only USD is supported in this demo")
    unavailable = False
    response: dict[str, Any] | None = None
    correlation_id = uuid4().hex
    with get_connection() as conn:
        status, version, reason = _checkout_probe(conn)
        if status != "healthy":
            _event(
                conn,
                level="ERROR",
                event_type="checkout.failed",
                service=SERVICE_NAME,
                message="Checkout rejected because the active service is unhealthy",
                details={"version": version, "reason": reason or "unhealthy", "correlation_id": correlation_id},
            )
            unavailable = True
        else:
            customer = conn.execute(
                "SELECT c.id,c.slug FROM customers c "
                "JOIN customer_service_subscriptions css ON css.customer_id=c.id "
                "JOIN services s ON s.id=css.service_id "
                "WHERE c.slug=%s AND s.service_key='checkout-api' AND css.status='active'",
                (request.customer_slug,),
            ).fetchone()
            if not customer:
                raise HTTPException(status_code=404, detail="Checkout customer not found or not subscribed")
            order = conn.execute(
                "INSERT INTO orders(customer_id,amount,currency,status) VALUES (%s,%s,%s,'created') "
                "RETURNING id,customer_id,amount,currency,status,created_at",
                (customer["id"], request.amount, request.currency.upper()),
            ).fetchone()
            _event(
                conn,
                level="INFO",
                event_type="checkout.created",
                service=SERVICE_NAME,
                message="Checkout order created",
                details={"version": version, "order_id": order["id"], "customer_slug": customer["slug"], "correlation_id": correlation_id},
            )
            response = {
                "order_id": order["id"],
                "customer_slug": customer["slug"],
                "amount": str(order["amount"]),
                "currency": order["currency"],
                "status": order["status"],
                "created_at": order["created_at"].isoformat(),
            }
    if unavailable:
        raise HTTPException(
            status_code=503,
            detail="Checkout unavailable: active release is incompatible with checkout configuration.",
        )
    assert response is not None
    return response


@app.get("/orders/{order_id}")
def get_order(order_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT o.id,o.amount,o.currency,o.status,o.created_at,c.slug AS customer_slug "
            "FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.id=%s",
            (order_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "order_id": row["id"],
        "customer_slug": row["customer_slug"],
        "amount": str(row["amount"]),
        "currency": row["currency"],
        "status": row["status"],
        "created_at": row["created_at"].isoformat(),
    }


@app.post("/deploy")
def deploy(request: DeployRequest) -> dict[str, Any]:
    if request.version not in {CURRENT_VERSION, BAD_VERSION}:
        raise HTTPException(status_code=400, detail="Unsupported demo version")
    with get_connection() as conn:
        conn.execute(
            "UPDATE service_state SET version=%s,status='healthy',updated_at=NOW() "
            "WHERE service_id=(SELECT id FROM services WHERE service_key='checkout-api')",
            (request.version,),
        )
        status, _, reason = _checkout_probe(conn)
        outcome = "degraded" if status != "healthy" else "succeeded"
        note = "Configuration compatibility check failed" if reason else "Release is healthy"
        conn.execute(
            "INSERT INTO deployments(service_id,version,outcome,deployed_at,note) "
            "SELECT id,%s,%s,NOW(),%s FROM services WHERE service_key='checkout-api'",
            (request.version, outcome, note),
        )
        _event(
            conn,
            level="ERROR" if status != "healthy" else "INFO",
            event_type="deployment.degraded" if status != "healthy" else "deployment.succeeded",
            service=SERVICE_NAME,
            message="Release deployed; checkout compatibility check failed" if reason else "Release deployed successfully",
            details={"version": request.version, "outcome": outcome, "reason": reason},
        )
    return {"version": request.version, "status": status, "outcome": outcome}


@app.post("/rollback")
def rollback() -> dict[str, Any]:
    with get_connection() as conn:
        previous = conn.execute(
            "SELECT ss.version,ss.status FROM service_state ss JOIN services s ON s.id=ss.service_id "
            "WHERE s.service_key='checkout-api'"
        ).fetchone()
        if not previous or (previous["version"] == CURRENT_VERSION and previous["status"] == "healthy"):
            raise HTTPException(status_code=409, detail="Checkout is already on the healthy release")
        conn.execute(
            "UPDATE service_state SET version=%s,status='healthy',updated_at=NOW() "
            "WHERE service_id=(SELECT id FROM services WHERE service_key='checkout-api')",
            (CURRENT_VERSION,),
        )
        conn.execute(
            "INSERT INTO deployments(service_id,version,outcome,deployed_at,note) "
            "SELECT id,%s,'succeeded',NOW(),'Rollback to last healthy release' "
            "FROM services WHERE service_key='checkout-api'",
            (CURRENT_VERSION,),
        )
        _event(
            conn,
            level="INFO",
            event_type="deployment.rollback",
            service=SERVICE_NAME,
            message="Rolled back to the last healthy release",
            details={"version": CURRENT_VERSION, "previous_version": previous["version"], "target_version": CURRENT_VERSION, "outcome": "succeeded"},
        )
    return {"version": CURRENT_VERSION, "status": "healthy", "outcome": "succeeded"}


@app.get("/logs")
def logs() -> dict[str, list[dict[str, Any]]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id,level,event_type,service,message,details,created_at "
            "FROM application_events ORDER BY created_at DESC,id DESC LIMIT 100"
        ).fetchall()
    return {"events": [_event_view(row) for row in rows]}


@app.get("/customers")
def customers() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT c.id,c.slug,c.name,c.email,c.company,c.segment,c.created_at,"
            "sub.plan,sub.monthly_amount,sub.currency,sub.status AS subscription_status,"
            "COALESCE(jsonb_agg(jsonb_build_object('name',s.name,'service_key',s.service_key,'status',css.status)) "
            "FILTER (WHERE s.id IS NOT NULL),'[]'::jsonb) AS services "
            "FROM customers c LEFT JOIN subscriptions sub ON sub.customer_id=c.id "
            "LEFT JOIN customer_service_subscriptions css ON css.customer_id=c.id "
            "LEFT JOIN services s ON s.id=css.service_id "
            "GROUP BY c.id,sub.plan,sub.monthly_amount,sub.currency,sub.status ORDER BY c.id"
        ).fetchall()
    return [
        {
            "slug": row["slug"], "name": row["name"], "email": row["email"],
            "company": row["company"], "segment": row["segment"],
            "created_at": row["created_at"].isoformat(),
            "subscription": None if row["plan"] is None else {
                "plan": row["plan"], "monthly_amount": str(row["monthly_amount"]),
                "currency": row["currency"], "status": row["subscription_status"],
            },
            "services": row["services"],
        }
        for row in rows
    ]


@app.post("/demo/reset")
def demo_reset() -> dict[str, str]:
    reset_demo()
    return {"status": "reset"}


@app.get("/demo/state")
def demo_state() -> dict[str, Any]:
    with get_connection() as conn:
        service_rows = conn.execute(
            "SELECT s.name,s.service_key,ss.status,ss.version FROM services s "
            "JOIN service_state ss ON ss.service_id=s.id ORDER BY s.id"
        ).fetchall()
        checkout_health, checkout_version, _ = _checkout_probe(conn)
        counts = conn.execute(
            "SELECT (SELECT count(*) FROM customers) AS customers,"
            "(SELECT count(*) FROM customer_service_subscriptions css JOIN services s ON s.id=css.service_id "
            "WHERE s.service_key='checkout-api' AND css.status='active') AS checkout_customers,"
            "(SELECT count(*) FROM customers WHERE segment='Enterprise') AS enterprise_customers,"
            "(SELECT count(*) FROM subscriptions WHERE status='active') AS subscriptions,"
            "(SELECT count(*) FROM deployments) AS deployments,"
            "(SELECT count(*) FROM historical_incidents) AS incidents,"
            "(SELECT count(*) FROM historical_service_cases) AS service_cases"
        ).fetchone()
        deployments = conn.execute(
            "SELECT d.id,d.version,d.outcome,d.deployed_at,d.note,s.name AS service "
            "FROM deployments d JOIN services s ON s.id=d.service_id "
            "ORDER BY d.deployed_at DESC,d.id DESC LIMIT 8"
        ).fetchall()
        incidents = conn.execute(
            "SELECT incident_key,title,severity,status,service,summary,affected_customer_count,started_at,resolved_at "
            "FROM historical_incidents ORDER BY started_at DESC,id DESC"
        ).fetchall()
        cases = conn.execute(
            "SELECT h.case_key,h.subject,h.category,h.status,h.priority,h.opened_at,h.resolved_at,c.slug AS customer_slug "
            "FROM historical_service_cases h JOIN customers c ON c.id=h.customer_id "
            "ORDER BY h.opened_at DESC,h.id DESC"
        ).fetchall()
        events = conn.execute(
            "SELECT id,level,event_type,service,message,details,created_at FROM application_events "
            "ORDER BY created_at DESC,id DESC LIMIT 12"
        ).fetchall()
        last_checkout = conn.execute(
            "SELECT o.id,o.amount,o.currency,o.status,o.created_at,c.slug AS customer_slug "
            "FROM orders o JOIN customers c ON c.id=o.customer_id ORDER BY o.id DESC LIMIT 1"
        ).fetchone()
    return {
        "services": [
            {
                "name": r["name"], "service_key": r["service_key"],
                "status": checkout_health if r["service_key"] == "checkout-api" else r["status"],
                "version": checkout_version if r["service_key"] == "checkout-api" else r["version"],
            }
            for r in service_rows
        ],
        "summary": dict(counts),
        "recent_deployments": [
            {"id": r["id"], "version": r["version"], "outcome": r["outcome"], "service": r["service"], "note": r["note"], "timestamp": r["deployed_at"].isoformat()}
            for r in deployments
        ],
        "historical_incidents": [
            {"incident_key": r["incident_key"], "title": r["title"], "severity": r["severity"], "status": r["status"], "service": r["service"], "summary": r["summary"], "affected_customer_count": r["affected_customer_count"], "started_at": r["started_at"].isoformat(), "resolved_at": r["resolved_at"].isoformat()}
            for r in incidents
        ],
        "historical_service_cases": [
            {"case_key": r["case_key"], "customer_slug": r["customer_slug"], "subject": r["subject"], "category": r["category"], "status": r["status"], "priority": r["priority"], "opened_at": r["opened_at"].isoformat(), "resolved_at": r["resolved_at"].isoformat()}
            for r in cases
        ],
        "recent_events": [_event_view(r) for r in events],
        "last_checkout": None if not last_checkout else {
            "order_id": last_checkout["id"], "customer_slug": last_checkout["customer_slug"],
            "amount": str(last_checkout["amount"]), "currency": last_checkout["currency"],
            "status": last_checkout["status"], "timestamp": last_checkout["created_at"].isoformat(),
        },
    }
