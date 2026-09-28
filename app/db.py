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
