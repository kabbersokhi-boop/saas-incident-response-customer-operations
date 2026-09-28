"""Deterministic RelayCart sample data and activity reset."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from psycopg.types.json import Jsonb

from .db import get_connection, reset_incident_workflow_state

ANCHOR = datetime(2026, 9, 28, 0, 0, tzinfo=timezone.utc)
CURRENT_VERSION = "v1.8.1"
BAD_VERSION = "v1.8.2"
NEUTRAL_VERSION = "v1.8.3"
HEALTHY_VERSIONS = frozenset({CURRENT_VERSION, NEUTRAL_VERSION})
DEPLOYABLE_VERSIONS = HEALTHY_VERSIONS | {BAD_VERSION}
SERVICE_NAME = "checkout-api"

FIRST_NAMES = [
    "Avery", "Blake", "Casey", "Devon", "Emery", "Finley", "Gray", "Harper",
    "Indigo", "Jordan", "Kai", "Logan", "Morgan", "Noel", "Oakley", "Parker",
    "Quinn", "Riley", "Sage", "Taylor", "Uma", "Val", "Wren", "Xan", "Yael",
    "Zion", "Arden", "Briar", "Cameron", "Drew",
]
COMPANIES = [
    "Northstar Goods", "Juniper Supply", "Copper Finch", "Bright Harbor", "Lumen Market",
    "Cedar & Stone", "Mosaic Works", "Bluebird Retail", "Fieldnote Co", "Golden Hour",
    "Pinecone Labs", "Daybreak Studio", "Riverbend Shop", "Orbit Outfitters", "Common Thread",
    "Foxglove Market", "Kindred Commerce", "Maple House", "Paper Kite", "Sunroom Supply",
    "Wildwood Goods", "Cloudline Retail", "Marigold Shop", "Oxbow Trading", "Little Current",
    "Open Trail", "Goodwell Market", "Elm & Iron", "Tandem Goods", "Soft Landing",
]
SERVICES = [
    ("Checkout API", "checkout-api", "Processes customer checkouts and creates orders."),
    ("Billing API", "billing-api", "Manages customer billing and subscription changes."),
    ("Notification API", "notification-api", "Sends customer and operational notifications."),
]


def seed_baseline() -> None:
    """Insert the immutable demo baseline once, without duplicating seeded rows."""
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM customers LIMIT 1").fetchone()
        if exists:
            return

        for i, (name, key, description) in enumerate(SERVICES):
            conn.execute(
                "INSERT INTO services(name, service_key, description) VALUES (%s, %s, %s)",
                (name, key, description),
            )
            version = CURRENT_VERSION if i == 0 else "v1.8.0"
            conn.execute(
                "INSERT INTO service_state(service_id, status, version, updated_at) "
                "SELECT id, 'healthy', %s, %s FROM services WHERE service_key = %s",
                (version, ANCHOR, key),
            )

        # Include recognizable demo accounts while keeping every row synthetic.
        companies = ["Acme Bikes", "Ocean Apparel", "Coffee Club", "Urban Shoes", "FitGear", "BookBox"] + COMPANIES[6:]
        companies[20] = "Green Dental"
        tiers = ["Enterprise"] * 7 + ["Growth"] * 7 + ["Starter"] * 16
        tiers[1], tiers[7] = tiers[7], tiers[1]  # Ocean Apparel is Growth; retain seven Enterprise accounts.
        customer_ids: list[int] = []
        for i, (first, company, tier) in enumerate(zip(FIRST_NAMES, companies, tiers)):
            slug = "acme-bikes" if i == 0 else f"{company.lower().replace(' ', '-').replace('&', 'and')}-{i + 1:02d}"
            email = f"{first.lower()}.{i + 1:02d}@example.test"
            created = ANCHOR - timedelta(days=90 - ((i * 17) % 89))
            row = conn.execute(
                "INSERT INTO customers(slug, name, email, company, segment, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (slug, first + " " + ["Morgan", "Lee", "Patel", "Kim", "Reed"][i % 5], email, company, tier, created),
            ).fetchone()
            customer_ids.append(row["id"])

        plan_data = {"Enterprise": ("Enterprise", 499), "Growth": ("Growth", 149), "Starter": ("Starter", 49)}
        # Every account has a plan; exactly 18 are subscribed to the checkout service.
        for i in range(30):
            tier = tiers[i]
            plan, amount = plan_data[tier]
            conn.execute(
                "INSERT INTO subscriptions(customer_id, plan, monthly_amount, currency, started_at) "
                "VALUES (%s, %s, %s, 'USD', %s)",
                (customer_ids[i], plan, amount, ANCHOR - timedelta(days=2 + (i * 5) % 85)),
            )
        service_ids = {
            row["service_key"]: row["id"]
            for row in conn.execute("SELECT id, service_key FROM services").fetchall()
        }
        # Exactly 18 customers subscribe to checkout; the other service links vary.
        for i, customer_id in enumerate(customer_ids):
            if i < 18:
                conn.execute(
                    "INSERT INTO customer_service_subscriptions(customer_id,service_id,started_at) VALUES (%s,%s,%s)",
                    (customer_id, service_ids["checkout-api"], ANCHOR - timedelta(days=2 + (i * 5) % 85)),
                )
            if i < 12 or i in (16, 18, 22, 27):
                conn.execute(
                    "INSERT INTO customer_service_subscriptions(customer_id,service_id,started_at) VALUES (%s,%s,%s)",
                    (customer_id, service_ids["billing-api"], ANCHOR - timedelta(days=4 + (i * 3) % 80)),
                )
            if i % 2 == 0 or i in (19, 23, 28):
                conn.execute(
                    "INSERT INTO customer_service_subscriptions(customer_id,service_id,started_at) VALUES (%s,%s,%s)",
                    (customer_id, service_ids["notification-api"], ANCHOR - timedelta(days=5 + (i * 7) % 82)),
                )

        # Historical deployment history spans the prior ~90 days.
        for i in range(20):
            deployed = ANCHOR - timedelta(days=88 - i * 4, hours=(i * 3) % 24)
            version = "v1.6.0" if i < 5 else "v1.7.0" if i < 11 else "v1.8.0" if i < 19 else CURRENT_VERSION
            outcome = "rolled_back" if i in (4, 12) else "degraded" if i == 16 else "succeeded"
            service_key = "checkout-api" if i == 19 else ("checkout-api", "billing-api", "notification-api")[i % 3]
            conn.execute(
                "INSERT INTO deployments(service_id, version, outcome, deployed_at, note) "
                "SELECT id, %s, %s, %s, %s FROM services WHERE service_key = %s",
                (version, outcome, deployed, "Release validation" if outcome == "succeeded" else "Rollback or limited signal recorded", service_key),
            )

        incidents = [
            ("Elevated checkout latency", "SEV-2", "Checkout API", "Temporary latency during a traffic spike."),
            ("Payment provider timeout", "SEV-2", "Checkout API", "Upstream payment timeouts delayed some checkouts."),
            ("Checkout session authorization errors", "SEV-3", "Checkout API", "A session authorization edge case affected a small number of users."),
            ("Webhook delivery backlog", "SEV-3", "Notification API", "A queue backlog delayed billing notifications."),
            ("Currency display mismatch", "SEV-3", "Billing API", "A display rounding issue affected one currency view."),
            ("Retry storm after provider maintenance", "SEV-2", "Billing API", "Retries briefly increased worker queue depth."),
            ("Checkout validation regression", "SEV-2", "Checkout API", "A validation edge case blocked some international orders."),
            ("Slow invoice history query", "SEV-3", "Billing API", "A database query increased invoice history load time."),
            ("Transient checkout error alert", "SEV-3", "Checkout API", "A brief monitoring spike had no reproduced checkout or order impact."),
            ("Intermittent cart lookup failures", "SEV-3", "Checkout API", "A cache refresh caused intermittent cart lookup failures."),
        ]
        for i, (title, severity, service, summary) in enumerate(incidents):
            started = ANCHOR - timedelta(days=8 + i * 8, hours=i * 2)
            conn.execute(
                "INSERT INTO historical_incidents(incident_key,title,severity,status,service,summary,affected_customer_count,started_at,resolved_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (f"INC-{2601 + i:04d}", title, severity, "Closed - no impact" if i == 8 else "Resolved", service, summary, [12, 8, 2, 11, 5, 9, 6, 4, 0, 3][i], started, started + timedelta(minutes=22 + i * 13)),
            )

        subjects = [
            "Question about an order", "Subscription plan update", "Invoice copy requested", "Checkout help",
            "Billing date clarification", "Payment method update", "Portal access assistance", "Refund status",
            "Tax details correction", "Order confirmation missing", "Plan feature question", "Currency support",
            "Duplicate charge review", "Address update", "Subscription pause request", "Receipt download help",
            "Checkout validation question", "Enterprise onboarding", "Payment retry guidance", "Account contact update",
        ]
        categories = ["Billing", "Checkout", "Account", "Subscription", "Invoice"]
        for i, subject in enumerate(subjects):
            opened = ANCHOR - timedelta(days=3 + (i * 4) % 85, hours=i % 7)
            customer_id = customer_ids[(i * 7 + 2) % len(customer_ids)]
            conn.execute(
                "INSERT INTO historical_service_cases(case_key,customer_id,subject,category,status,priority,opened_at,resolved_at) "
                "VALUES (%s,%s,%s,%s,'Resolved',%s,%s,%s)",
                (f"CASE-{7101 + i:04d}", customer_id, subject, categories[i % len(categories)], "High" if i % 6 == 0 else "Normal", opened, opened + timedelta(hours=1 + (i * 7) % 35)),
            )

        # Intentionally old-format config: v1.8.2 assumes `pricing_rules` exists.
        conn.execute(
            "INSERT INTO config(config_key, value, updated_at) VALUES ('checkout', %s, %s)",
            (Jsonb({"currency_rules": {"USD": "2-decimal"}, "schema_version": 1}), ANCHOR),
        )
        conn.execute(
            "INSERT INTO config(config_key,value,updated_at) VALUES ('demo_checkout_fault',%s,%s)",
            (Jsonb({"enabled": False}), ANCHOR),
        )
        conn.execute(
            "INSERT INTO application_events(level,event_type,service,message,details,created_at) "
            "VALUES ('INFO','demo.initialized','RelayCart','Demo baseline initialized',%s,%s)",
            (Jsonb({"customers": 30, "subscriptions": 30, "checkout_subscriptions": 18}), ANCHOR),
        )


def reset_demo() -> None:
    """Remove demo activity and restore the seeded baseline and healthy version."""
    with get_connection() as conn:
        reset_incident_workflow_state(conn)
        conn.execute("TRUNCATE rollback_requests")
        conn.execute("TRUNCATE orders RESTART IDENTITY")
        conn.execute("TRUNCATE application_events RESTART IDENTITY")
        conn.execute("TRUNCATE deployments, health_failure_observations RESTART IDENTITY")
        conn.execute(
            "UPDATE service_state SET status='healthy', version=%s, updated_at=%s "
            "WHERE service_id=(SELECT id FROM services WHERE service_key='checkout-api')",
            (CURRENT_VERSION, ANCHOR),
        )
        # Rebuild the seeded deployment history exactly, keeping the helper idempotent.
        for i in range(20):
            deployed = ANCHOR - timedelta(days=88 - i * 4, hours=(i * 3) % 24)
            version = "v1.6.0" if i < 5 else "v1.7.0" if i < 11 else "v1.8.0" if i < 19 else CURRENT_VERSION
            outcome = "rolled_back" if i in (4, 12) else "degraded" if i == 16 else "succeeded"
            service_key = "checkout-api" if i == 19 else ("checkout-api", "billing-api", "notification-api")[i % 3]
            conn.execute(
                "INSERT INTO deployments(service_id,version,outcome,deployed_at,note) "
                "SELECT id,%s,%s,%s,%s FROM services WHERE service_key=%s",
                (version, outcome, deployed, "Release validation" if outcome == "succeeded" else "Rollback or limited signal recorded", service_key),
            )
        conn.execute("UPDATE config SET value=%s, updated_at=%s WHERE config_key='checkout'", (Jsonb({"currency_rules": {"USD": "2-decimal"}, "schema_version": 1}), ANCHOR))
        conn.execute(
            "INSERT INTO config(config_key,value,updated_at) VALUES ('demo_checkout_fault',%s,%s) "
            "ON CONFLICT (config_key) DO UPDATE SET value=EXCLUDED.value,updated_at=EXCLUDED.updated_at",
            (Jsonb({"enabled": False}), ANCHOR),
        )
        conn.execute(
            "INSERT INTO application_events(level,event_type,service,message,details,created_at) "
            "VALUES ('INFO','demo.initialized','RelayCart','Demo baseline initialized',%s,%s)",
            (Jsonb({"customers": 30, "subscriptions": 30, "checkout_subscriptions": 18}), ANCHOR),
        )
