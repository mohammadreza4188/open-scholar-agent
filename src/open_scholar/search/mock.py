"""Offline search provider returning clearly-labelled fixtures (never real opportunities)."""
from __future__ import annotations

from .base import ProviderInfo, SearchProvider, SearchResult


class MockSearchProvider(SearchProvider):
    info = ProviderInfo(
        name="mock", requires_api_key=False, pricing="free",
        coverage="none (fixtures only)",
        limitations=["Returns fake example.org URLs for local development and tests."],
    )

    def __init__(self, results: list[SearchResult] | None = None, fail: bool = False):
        self._results = results
        self._fail = fail

    async def search(self, query: str, *, max_results: int = 10) -> list[SearchResult]:
        from .base import SearchError
        if self._fail:
            raise SearchError("mock failure")
        if self._results is not None:
            return self._results[:max_results]
        return [SearchResult(
            title=f"[MOCK] Example funded MSc in AI ({query})",
            url="https://example.org/mock/msc-ai",
            snippet="Mock fixture - not a real opportunity.", provider=self.name)][:max_results]
