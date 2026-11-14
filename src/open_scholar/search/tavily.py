"""Tavily Search API adapter (official API; key sent as a Bearer token)."""
from __future__ import annotations

import httpx

from .base import ProviderInfo, SearchError, SearchProvider, SearchResult, check_response, clean_snippet, is_http_url

TAVILY_URL = "https://api.tavily.com/search"


class TavilySearchProvider(SearchProvider):
    info = ProviderInfo(
        name="tavily", requires_api_key=True,
        pricing="Credit-based, with a limited free tier - verify at https://tavily.com",
        rate_limits="Plan-dependent (HTTP 429 when exceeded).",
        terms_url="https://tavily.com",
        coverage="General web, worldwide; AI-oriented result extraction.",
        limitations=["Results are discovery hints only, never verification evidence."],
    )

    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None, url: str = TAVILY_URL):
        if not api_key:
            raise ValueError("Tavily API key required")
        self._key, self._url = api_key, url
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def search(self, query: str, *, max_results: int = 10) -> list[SearchResult]:
        try:
            r = await self._client.post(
                self._url, headers={"Authorization": f"Bearer {self._key}"},
                json={"query": query, "max_results": min(max(max_results, 1), 20), "search_depth": "basic"})
        except httpx.HTTPError as e:
            raise SearchError(f"tavily: network error ({type(e).__name__})") from None
        check_response("tavily", r)
        try:
            items = r.json().get("results") or []
        except ValueError:
            raise SearchError("tavily: response was not JSON") from None
        out = [SearchResult(title=clean_snippet(i.get("title")), url=i["url"],
                            snippet=clean_snippet(i.get("content"))[:500], provider="tavily")
               for i in items if isinstance(i, dict) and is_http_url(i.get("url"))]
        return out[:max_results]
