"""Search provider abstraction. Providers are interchangeable and optional."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    provider: str = ""
    # Snippets are discovery hints only; they are NEVER verification evidence.


class SearchError(Exception):
    """Raised for provider failures (network, auth, rate limit)."""


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
