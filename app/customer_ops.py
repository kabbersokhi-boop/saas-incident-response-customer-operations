"""Read-only HighLevel audit helpers; n8n owns customer-ops orchestration."""

from __future__ import annotations

import time

import httpx

OBJECT = "custom_objects.relaycart_service_case"
ASSOCIATION_ID = "6abb11b64427829e84164de5"


def _request(client: httpx.Client, method: str, path: str, **kwargs) -> dict:
    """Bounded, token-safe request for synthetic audit/cleanup scripts only."""
    response = client.request(method, path, **kwargs)
    time.sleep(0.7)
    if not response.is_success:
        raise RuntimeError(f"HighLevel {method} {path} returned HTTP {response.status_code}")
    result = response.json()
    if not isinstance(result, dict):
        raise RuntimeError("HighLevel returned a non-object response")
    return result
