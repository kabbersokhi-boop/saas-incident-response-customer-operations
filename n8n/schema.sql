-- Phase 2 incident-response state owned by n8n.
-- Apply to RelayCart's demo Postgres database with `psql -v ON_ERROR_STOP=1`.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS ir_events (
    event_id TEXT PRIMARY KEY,
    source TEXT NOT NULL CHECK (length(source) BETWEEN 1 AND 80),
    event_type TEXT NOT NULL CHECK (event_type IN (
        'deployment.completed', 'health.failed', 'checkout.failed', 'manual.test'
    )),
    service TEXT NOT NULL CHECK (length(service) BETWEEN 1 AND 120),
    environment TEXT NOT NULL CHECK (length(environment) BETWEEN 1 AND 80),
    occurred_at TIMESTAMPTZ NOT NULL,
    correlation_hint TEXT,
    severity_hint TEXT CHECK (severity_hint IS NULL OR severity_hint IN ('SEV-1', 'SEV-2', 'SEV-3')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ir_events_service_time_idx
    ON ir_events (service, environment, occurred_at DESC);
CREATE INDEX IF NOT EXISTS ir_events_correlation_idx
    ON ir_events (correlation_hint) WHERE correlation_hint IS NOT NULL;

CREATE TABLE IF NOT EXISTS ir_incidents (
    incident_id TEXT PRIMARY KEY DEFAULT ('INC-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 12))),
    service TEXT NOT NULL,
    environment TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('SEV-1', 'SEV-2', 'SEV-3')),
    state TEXT NOT NULL CHECK (state IN (
        'OPEN', 'INVESTIGATING', 'WAITING_FOR_APPROVAL', 'REMEDIATING',
        'VERIFYING', 'NEEDS_ATTENTION', 'RECOVERED', 'RESOLVED'
    )),
    correlation_key TEXT NOT NULL,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    latest_event_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_version TEXT,
    healthy_version TEXT,
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
    summary TEXT,
    recovered_at TIMESTAMPTZ
);

-- At most one live incident for a service/environment pair. NEEDS_ATTENTION is
-- intentionally live so new signals enrich the incident that still needs action.
CREATE UNIQUE INDEX IF NOT EXISTS ir_incidents_one_active_service_idx
    ON ir_incidents (service, environment)
    WHERE state NOT IN ('RECOVERED', 'RESOLVED');
CREATE INDEX IF NOT EXISTS ir_incidents_state_time_idx
    ON ir_incidents (state, updated_at DESC);

CREATE TABLE IF NOT EXISTS ir_incident_events (
    incident_id TEXT NOT NULL REFERENCES ir_incidents(incident_id) ON DELETE CASCADE,
    event_id TEXT NOT NULL REFERENCES ir_events(event_id) ON DELETE CASCADE,
    relationship TEXT NOT NULL CHECK (relationship IN ('trigger', 'related', 'deployment_context')),
    linked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (incident_id, event_id)
);
CREATE INDEX IF NOT EXISTS ir_incident_events_event_idx ON ir_incident_events (event_id);

CREATE TABLE IF NOT EXISTS ir_evidence (
    evidence_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES ir_incidents(incident_id) ON DELETE CASCADE,
    evidence_key TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN (
        'event', 'release_state', 'health_check', 'application_log',
        'synthetic_checkout', 'order_readback', 'policy'
    )),
    summary TEXT NOT NULL CHECK (length(summary) <= 2000),
    source_event_id TEXT REFERENCES ir_events(event_id) ON DELETE SET NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(payload) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (incident_id, evidence_key)
);
CREATE INDEX IF NOT EXISTS ir_evidence_incident_idx ON ir_evidence (incident_id, evidence_id);

CREATE TABLE IF NOT EXISTS ir_assessments (
    assessment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES ir_incidents(incident_id) ON DELETE CASCADE,
    revision INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'valid', 'invalid', 'unavailable', 'stale')),
    provider TEXT NOT NULL,
    model TEXT,
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    assessment JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(assessment) = 'object'),
    validation_errors JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(validation_errors) = 'array'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (incident_id, revision)
);
ALTER TABLE ir_assessments DROP CONSTRAINT IF EXISTS ir_assessments_status_check;
ALTER TABLE ir_assessments ADD CONSTRAINT ir_assessments_status_check
    CHECK (status IN ('pending', 'valid', 'invalid', 'unavailable', 'stale'));

CREATE TABLE IF NOT EXISTS ir_proposals (
    proposal_id TEXT PRIMARY KEY DEFAULT ('RMP-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 12))),
    incident_id TEXT NOT NULL REFERENCES ir_incidents(incident_id) ON DELETE CASCADE,
    revision INTEGER NOT NULL CHECK (revision > 0),
    action_type TEXT NOT NULL CHECK (action_type IN ('rollback', 'observe', 'escalate', 'none')),
    source_version TEXT,
    target_version TEXT,
    reason TEXT NOT NULL CHECK (length(reason) <= 2000),
    evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(evidence_refs) = 'array'),
    status TEXT NOT NULL CHECK (status IN (
        'PROPOSED', 'APPROVED', 'REJECTED', 'EXPIRED', 'STALE', 'EXECUTED', 'CANCELLED'
    )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    UNIQUE (incident_id, revision),
    CHECK (action_type <> 'rollback' OR (source_version IS NOT NULL AND target_version IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS ir_approvals (
    approval_id TEXT PRIMARY KEY DEFAULT ('APR-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 12))),
    proposal_id TEXT NOT NULL UNIQUE REFERENCES ir_proposals(proposal_id) ON DELETE CASCADE,
    proposal_revision INTEGER NOT NULL,
    action_type TEXT NOT NULL CHECK (action_type IN ('rollback', 'observe', 'escalate', 'none')),
    source_version TEXT,
    target_version TEXT,
    delivery_token UUID NOT NULL DEFAULT gen_random_uuid(),
    token_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED', 'CONSUMED')),
    decision TEXT CHECK (decision IS NULL OR decision IN ('approve', 'reject')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    decided_at TIMESTAMPTZ,
    consumed_at TIMESTAMPTZ,
    CHECK (action_type <> 'rollback' OR (source_version IS NOT NULL AND target_version IS NOT NULL))
);
ALTER TABLE ir_approvals ADD COLUMN IF NOT EXISTS delivery_token UUID;
UPDATE ir_approvals SET delivery_token = gen_random_uuid() WHERE delivery_token IS NULL;
ALTER TABLE ir_approvals ALTER COLUMN delivery_token SET DEFAULT gen_random_uuid();
ALTER TABLE ir_approvals ALTER COLUMN delivery_token SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ir_approvals_delivery_token_idx ON ir_approvals (delivery_token);

CREATE TABLE IF NOT EXISTS ir_remediation_attempts (
    attempt_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    proposal_id TEXT NOT NULL REFERENCES ir_proposals(proposal_id) ON DELETE CASCADE,
    approval_id TEXT NOT NULL REFERENCES ir_approvals(approval_id) ON DELETE CASCADE,
    request_id TEXT NOT NULL UNIQUE,
    source_version TEXT NOT NULL,
    target_version TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('succeeded', 'failed', 'blocked', 'stale')),
    http_status INTEGER,
    observed_version TEXT,
    response JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(response) = 'object'),
    error TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS ir_verification_checks (
    verification_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    attempt_id BIGINT NOT NULL REFERENCES ir_remediation_attempts(attempt_id) ON DELETE CASCADE,
    check_name TEXT NOT NULL CHECK (check_name IN (
        'version', 'health', 'synthetic_checkout', 'order_readback'
    )),
    expected TEXT,
    observed TEXT,
    passed BOOLEAN NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(details) = 'object'),
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (attempt_id, check_name)
);

CREATE TABLE IF NOT EXISTS ir_poll_state (
    poller_name TEXT PRIMARY KEY,
    last_occurred_at TIMESTAMPTZ,
    last_source_id BIGINT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO ir_poll_state (poller_name)
VALUES ('relaycart-application-events')
ON CONFLICT (poller_name) DO NOTHING;
