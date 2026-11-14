"""Shared HTTP helper for LLM adapters: error mapping that never leaks credentials."""
from __future__ import annotations

from typing import Any

import httpx

from .base import LLMError


def make_client(client: httpx.AsyncClient | None) -> httpx.AsyncClient:
    return client or httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0))


async def post_json(client: httpx.AsyncClient, provider: str, url: str, headers: dict[str, str],
                    payload: dict[str, Any]) -> dict[str, Any]:
    try:
        r = await client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as e:
        raise LLMError(f"{provider}: network error ({type(e).__name__})") from None
    if r.status_code in (401, 403):
        raise LLMError(f"{provider}: authentication failed (check the API key)")
    if r.status_code == 429:
        raise LLMError(f"{provider}: rate limited or quota exceeded")
    if r.status_code >= 400:
        detail = ""
        try:
            err = r.json().get("error")
            detail = (err.get("message") if isinstance(err, dict) else str(err or ""))[:200]
        except (ValueError, AttributeError):
            pass
        raise LLMError(f"{provider}: HTTP {r.status_code} {detail}".strip())
    try:
        return r.json()
    except ValueError:
        raise LLMError(f"{provider}: response was not JSON") from None
