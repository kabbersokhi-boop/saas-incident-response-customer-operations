"""Black-box checks for the repeatable Phase 1 interview demo."""

import os

import httpx
import pytest


BASE_URL = os.getenv("RELAYCART_BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture
def api():
    with httpx.Client(base_url=BASE_URL, timeout=15) as client:
        response = client.post("/demo/reset")
        assert response.status_code == 200, response.text
        yield client


def checkout(client, customer_slug="acme-bikes"):
    return client.post(
        "/checkout",
        json={"customer_slug": customer_slug, "amount": "129.99", "currency": "USD"},
    )


def test_healthy_checkout_is_a_durable_order(api):
    health = api.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert health.json()["version"] == "v1.8.1"

    created = checkout(api)
    assert created.status_code == 201, created.text
    order = created.json()
    assert order["status"] == "created"
    assert order["order_id"]

    read_back = api.get(f"/orders/{order['order_id']}")
    assert read_back.status_code == 200
    assert read_back.json()["order_id"] == order["order_id"]
    assert read_back.json()["status"] == "created"


def test_bad_deployment_changes_real_behavior_and_rollback_recovers(api):
    deployed = api.post("/deploy", json={"version": "v1.8.2"})
    assert deployed.status_code == 200, deployed.text

    health = api.get("/health")
    assert health.json()["status"] == "unhealthy"
    assert health.json()["version"] == "v1.8.2"
    failed = checkout(api)
    assert failed.status_code == 503, failed.text

    events_response = api.get("/logs")
    assert events_response.status_code == 200
    events = events_response.json()
    if isinstance(events, dict):
        events = events.get("events", events.get("logs", []))
    assert any(
        event.get("version") == "v1.8.2"
        and event.get("severity") in {"error", "ERROR"}
        and event.get("event_type")
        and event.get("timestamp")
        for event in events
    )

    rolled_back = api.post("/rollback")
    assert rolled_back.status_code == 200, rolled_back.text
    assert api.get("/health").json()["status"] == "healthy"
    assert api.get("/version").json()["version"] == "v1.8.1"
    recovered = checkout(api)
    assert recovered.status_code == 201, recovered.text
    order_id = recovered.json()["order_id"]
    assert api.get(f"/orders/{order_id}").status_code == 200


def test_reset_restores_same_seed_and_removes_demo_order(api):
    baseline = api.get("/demo/state").json()
    created = checkout(api)
    assert created.status_code == 201
    order_id = created.json()["order_id"]
    assert api.post("/deploy", json={"version": "v1.8.2"}).status_code == 200

    assert api.post("/demo/reset").status_code == 200
    restored = api.get("/demo/state").json()
    assert api.get("/health").json()["status"] == "healthy"
    assert api.get(f"/orders/{order_id}").status_code == 404
    for key in ("summary", "recent_deployments", "historical_incidents", "historical_service_cases"):
        assert restored[key] == baseline[key]
    assert restored.get("last_checkout") == baseline.get("last_checkout")


def test_business_history_and_validation(api):
    state = api.get("/demo/state").json()
    summary = state["summary"]
    assert summary["customers"] == 30
    assert summary["checkout_customers"] == 18
    assert summary["enterprise_customers"] == 7
    assert summary["subscriptions"] == 30
    assert summary["incidents"] == 10
    assert summary["service_cases"] == 20
    assert summary["deployments"] == 20
    customers = api.get("/customers").json()
    assert len(customers) == 30
    assert {customer["subscription"]["plan"] for customer in customers} == {
        "Starter", "Growth", "Enterprise"
    }
    assert sum(
        any(service["service_key"] == "checkout-api" for service in customer["services"])
        for customer in customers
    ) == 18
    assert all(customer["email"].endswith("@example.test") for customer in customers)
    assert any(customer["slug"] == "acme-bikes" for customer in customers)
    ocean = next(customer for customer in customers if customer["company"] == "Ocean Apparel")
    assert ocean["subscription"]["plan"] == "Growth"
    green = next(customer for customer in customers if customer["company"] == "Green Dental")
    assert green["subscription"]["plan"] == "Starter"
    assert {service["service_key"] for service in green["services"]} == {"notification-api"}
    assert all(0 <= incident["affected_customer_count"] <= 30 for incident in state["historical_incidents"])
    other_service_customer = next(
        customer for customer in customers
        if all(service["service_key"] != "checkout-api" for service in customer["services"])
    )
    assert checkout(api, other_service_customer["slug"]).status_code == 404

    bad_amount = api.post(
        "/checkout",
        json={"customer_slug": "acme-bikes", "amount": "-1", "currency": "USD"},
    )
    assert bad_amount.status_code in {400, 422}
    unsupported_currency = api.post(
        "/checkout",
        json={"customer_slug": "acme-bikes", "amount": "1.00", "currency": "EUR"},
    )
    assert unsupported_currency.status_code in {400, 422}
    unknown_customer = checkout(api, "no-such-merchant")
    assert unknown_customer.status_code in {400, 404, 422}
    invalid_deploy = api.post("/deploy", json={"version": "v9.9.9"})
    assert invalid_deploy.status_code in {400, 422}
    assert api.get("/version").json()["version"] == "v1.8.1"
