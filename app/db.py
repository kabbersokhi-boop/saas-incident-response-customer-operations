"""Database setup and small connection helpers for RelayCart."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row


def database_url() -> str:
    """Return the configured PostgreSQL URL without ever logging it."""
    return os.environ.get(
        "DATABASE_URL", "postgresql://relaycart:relaycart_demo_only@localhost:5432/relaycart"
    )


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(database_url(), row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT NOT NULL,
    segment TEXT NOT NULL CHECK (segment IN ('Starter', 'Growth', 'Enterprise')),
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    service_key TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    plan TEXT NOT NULL,
    monthly_amount NUMERIC(10,2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    status TEXT NOT NULL DEFAULT 'active',
    started_at TIMESTAMPTZ NOT NULL,
    UNIQUE(customer_id)
);
CREATE TABLE IF NOT EXISTS customer_service_subscriptions (
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'active',
    started_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY(customer_id, service_id)
);
CREATE TABLE IF NOT EXISTS service_state (
    service_id INTEGER PRIMARY KEY REFERENCES services(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'healthy',
    version TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS deployments (
    id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES services(id),
    version TEXT NOT NULL,
    outcome TEXT NOT NULL,
    deployed_at TIMESTAMPTZ NOT NULL,
    note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS orders (
    id BIGSERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    currency TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS application_events (
    id BIGSERIAL PRIMARY KEY,
    level TEXT NOT NULL,
    event_type TEXT NOT NULL,
    service TEXT NOT NULL,
    message TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS health_failure_observations (
    deployment_id INTEGER PRIMARY KEY REFERENCES deployments(id) ON DELETE CASCADE,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS rollback_requests (
    request_id TEXT PRIMARY KEY,
    source_version TEXT NOT NULL,
    target_version TEXT NOT NULL,
    response JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS historical_incidents (
    id SERIAL PRIMARY KEY,
    incident_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    service TEXT NOT NULL,
    summary TEXT NOT NULL,
    affected_customer_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS historical_service_cases (
    id SERIAL PRIMARY KEY,
    case_key TEXT NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    subject TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    opened_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ NOT NULL
);
ALTER TABLE historical_incidents ADD COLUMN IF NOT EXISTS affected_customer_count INTEGER NOT NULL DEFAULT 0;
UPDATE historical_incidents SET severity='SEV-3' WHERE severity='SEV-4';
CREATE TABLE IF NOT EXISTS config (
    config_key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON application_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_deployments_deployed_at ON deployments(deployed_at DESC);
"""


def initialize_schema() -> None:
    with get_connection() as conn:
        conn.execute(SCHEMA)


def incident_workflow_schema_available(conn: psycopg.Connection) -> bool:
    """Return whether the complete optional n8n-owned schema is installed."""
    return conn.execute(
        "SELECT to_regclass('ir_events') IS NOT NULL "
        "AND to_regclass('ir_incidents') IS NOT NULL "
        "AND to_regclass('ir_incident_events') IS NOT NULL "
        "AND to_regclass('ir_evidence') IS NOT NULL "
        "AND to_regclass('ir_assessments') IS NOT NULL "
        "AND to_regclass('ir_proposals') IS NOT NULL "
        "AND to_regclass('ir_approvals') IS NOT NULL "
        "AND to_regclass('ir_remediation_attempts') IS NOT NULL "
        "AND to_regclass('ir_verification_checks') IS NOT NULL "
        "AND to_regclass('ir_poll_state') IS NOT NULL AS all_tables_present"
    ).fetchone()["all_tables_present"]


def reset_incident_workflow_state(conn: psycopg.Connection) -> None:
    """Clear Phase 2 state when its optional n8n-owned schema is installed.

    RelayCart must still start and reset cleanly before Phase 2 creates these
    tables. Check the complete table set first so partially applied DDL stays
    untouched and no CASCADE can reach unrelated data.
    """
    if incident_workflow_schema_available(conn):
        conn.execute(
            "TRUNCATE TABLE ir_verification_checks, ir_remediation_attempts, "
            "ir_approvals, ir_proposals, ir_assessments, ir_evidence, "
            "ir_incident_events, ir_events, ir_incidents, ir_poll_state "
            "RESTART IDENTITY"
        )
