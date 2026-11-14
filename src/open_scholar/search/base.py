"""Search provider abstraction. Providers are interchangeable and optional."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    provider: str = ""
    # Snippets are discovery hints only; they are NEVER verification evidence.


class SearchError(Exception):
    """Raised for provider failures (network, auth, rate limit). Never contains API keys."""


@dataclass
class ProviderInfo:
    """Documentation metadata required by MISSION.md section 4.4."""
    name: str
    requires_api_key: bool = False
    pricing: str = "unknown"
    rate_limits: str = "unknown"
    terms_url: str | None = None
    coverage: str = "unknown"
    limitations: list[str] = field(default_factory=list)


class SearchProvider(ABC):
    info: ProviderInfo

    @property
    def name(self) -> str:
        return self.info.name

    @abstractmethod
    async def search(self, query: str, *, max_results: int = 10) -> list[SearchResult]:
        """Return discovery results or raise SearchError."""


def clean_snippet(text: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text or "")).strip()


def is_http_url(url: object) -> bool:
    return isinstance(url, str) and urlparse(url).scheme in ("http", "https") and bool(urlparse(url).netloc)


def check_response(provider: str, r: httpx.Response) -> None:
    if r.status_code in (401, 403):
        raise SearchError(f"{provider}: authentication failed (check the API key)")
    if r.status_code == 429:
        raise SearchError(f"{provider}: rate limited or quota exceeded")
    if r.status_code != 200:
        raise SearchError(f"{provider}: HTTP {r.status_code}")
