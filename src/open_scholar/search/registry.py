"""Provider registry/factory. Falls back to the mock provider when no keys exist."""
from __future__ import annotations

import logging

import httpx

from open_scholar.config.settings import Settings

from .base import SearchError, SearchProvider, SearchResult
from .brave import BraveSearchProvider
from .mock import MockSearchProvider
from .tavily import TavilySearchProvider

log = logging.getLogger(__name__)


def build_providers(settings: Settings, client: httpx.AsyncClient | None = None) -> list[SearchProvider]:
    providers: list[SearchProvider] = []
    if settings.brave_api_key:
        providers.append(BraveSearchProvider(settings.brave_api_key, client))
    if settings.tavily_api_key:
        providers.append(TavilySearchProvider(settings.tavily_api_key, client))
    if not providers:
        log.warning("No search API keys configured; using MockSearchProvider.")
        providers.append(MockSearchProvider())
    return providers


async def search_all(providers: list[SearchProvider], query: str):
    """Query every provider; report which succeeded/failed (coverage transparency)."""
    results: list[SearchResult] = []
    checked: list[str] = []
    failed: dict[str, str] = {}
    for p in providers:
        try:
            results.extend(await p.search(query))
            checked.append(p.name)
        except SearchError as e:
            failed[p.name] = str(e)
    return results, checked, failed
