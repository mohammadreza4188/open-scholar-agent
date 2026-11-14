"""Provider registry/factory. Falls back to the mock provider when no keys exist."""
from __future__ import annotations

import logging

from open_scholar.config.settings import Settings

from .base import SearchError, SearchProvider, SearchResult
from .mock import MockSearchProvider

log = logging.getLogger(__name__)


def build_providers(settings: Settings) -> list[SearchProvider]:
    providers: list[SearchProvider] = []
    # TODO(Phase 1b): BraveSearchProvider(settings.brave_api_key), TavilyProvider(...)
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
