"""Deterministic offline LLM stand-in. Invents nothing: everything is 'unknown'."""
from __future__ import annotations

from typing import Any

from .base import LLMProvider


class MockLLMProvider(LLMProvider):
    name = "mock"

    async def extract_requirements(self, page_content: str) -> dict[str, Any]:
        return {"degree_requirement": None, "student_status_requirement": None,
                "deadline": None, "funding": "unknown", "source": "mock"}

    async def analyze_opportunity(self, opportunity, profile):
        return {"summary": "Mock analysis (no LLM configured).", "unresolved": ["all"]}

    async def generate_application_document(self, context) -> str:
        return "[MOCK DOCUMENT] No LLM configured."


def get_llm(provider: str) -> LLMProvider | None:
    """Return None when LLM is disabled. Real adapters arrive in Phase 2."""
    if provider in ("none", ""):
        return None
    if provider == "mock":
        return MockLLMProvider()
    raise NotImplementedError(f"LLM provider {provider!r} is planned for Phase 2")
