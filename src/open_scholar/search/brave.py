"""Brave Search API adapter (official API; key sent in a header)."""
from __future__ import annotations

import httpx

from .base import ProviderInfo, SearchError, SearchProvider, SearchResult, check_response, clean_snippet, is_http_url

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveSearchProvider(SearchProvider):
    info = ProviderInfo(
        name="brave", requires_api_key=True,
        pricing="Paid and/or limited free plans - verify current plans at https://brave.com/search/api/",
        rate_limits="Plan-dependent (HTTP 429 when exceeded); verify in your Brave dashboard.",
        terms_url="https://brave.com/search/api/",
        coverage="General web index, worldwide.",
        limitations=["Results are discovery hints only, never verification evidence.",
                     "Check your plan's terms before storing or redistributing results."],
    )

    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None, url: str = BRAVE_URL):
        if not api_key:
            raise ValueError("Brave API key required")
        self._key, self._url = api_key, url
        self._client = client or httpx.AsyncClient(timeout=20.0)

    async def search(self, query: str, *, max_results: int = 10) -> list[SearchResult]:
        try:
            r = await self._client.get(
                self._url, params={"q": query, "count": min(max(max_results, 1), 20)},
                headers={"X-Subscription-Token": self._key, "Accept": "application/json"})
        except httpx.HTTPError as e:
            raise SearchError(f"brave: network error ({type(e).__name__})") from None
        check_response("brave", r)
        try:
            items = (r.json().get("web") or {}).get("results") or []
        except ValueError:
            raise SearchError("brave: response was not JSON") from None
        out = [SearchResult(title=clean_snippet(i.get("title")), url=i["url"],
                            snippet=clean_snippet(i.get("description")), provider="brave")
               for i in items if isinstance(i, dict) and is_http_url(i.get("url"))]
        return out[:max_results]
