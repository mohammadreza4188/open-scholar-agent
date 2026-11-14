"""Deterministic offline LLM stand-in. Invents nothing: everything is 'unknown'."""
from __future__ import annotations

from .base import LLMProvider, Usage


class MockLLMProvider(LLMProvider):
    name = "mock"
    model = "mock"

    def __init__(self, reply: str = "{}", usage: Usage | None = None) -> None:
        super().__init__()
        self.reply, self.usage = reply, usage or Usage()
        self.calls: list[tuple[str, str]] = []

    async def _complete(self, system: str, user: str, *, json_mode: bool):
        self.calls.append((system, user))
        return self.reply, self.usage
