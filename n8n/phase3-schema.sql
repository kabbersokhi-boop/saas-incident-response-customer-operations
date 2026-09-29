-- Customer operations projection. Technical incident state remains in ir_*.
CREATE TABLE IF NOT EXISTS ghl_contacts (
    customer_key TEXT PRIMARY KEY REFERENCES customers(slug),
    location_id TEXT NOT NULL,
    contact_id TEXT NOT NULL UNIQUE,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ghl_effects (
    effect_id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES ir_incidents(incident_id) ON DELETE CASCADE,
    customer_key TEXT NOT NULL REFERENCES customers(slug),
    effect_type TEXT NOT NULL CHECK (effect_type = 'service_case'),
    desired_state JSONB NOT NULL CHECK (jsonb_typeof(desired_state) = 'object'),
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','RETRY','SUCCEEDED')),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ghl_record_id TEXT,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (incident_id, customer_key, effect_type)
);
CREATE INDEX IF NOT EXISTS ghl_effects_due_idx ON ghl_effects (next_attempt_at) WHERE status <> 'SUCCEEDED';

CREATE TABLE IF NOT EXISTS ghl_customer_feedback (
    incident_id TEXT NOT NULL REFERENCES ir_incidents(incident_id) ON DELETE CASCADE,
    customer_key TEXT NOT NULL REFERENCES customers(slug),
    ghl_record_id TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('CONFIRMED_RESOLVED','NEEDS_FOLLOW_UP')),
    occurred_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (incident_id, customer_key, outcome)
);
