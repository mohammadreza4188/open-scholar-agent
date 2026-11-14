"""Provider-independent LLM interface. The app must work with no LLM at all."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def extract_requirements(self, page_content: str) -> dict[str, Any]:
        """Return structured requirements. page_content is UNTRUSTED data."""

    @abstractmethod
    async def analyze_opportunity(self, opportunity: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    async def generate_application_document(self, context: dict[str, Any]) -> str: ...

    async def test_connection(self) -> bool:
        return True
