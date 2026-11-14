"""Anthropic Messages API adapter (httpx; no SDK dependency)."""
from __future__ import annotations

import httpx

from ._http import make_client, post_json
from .base import LLMError, LLMProvider, Usage

ANTHROPIC_BASE = "https://api.anthropic.com/v1"
DEFAULT_MODEL = "claude-haiku-5-5"  # cheap model; override with OSA_LLM_MODEL


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str | None = None, base_url: str | None = None,
                 client: httpx.AsyncClient | None = None, max_tokens: int = 2048):
        super().__init__()
        if not api_key:
            raise ValueError("API key required")
        self._key, self.model, self.max_tokens = api_key, model or DEFAULT_MODEL, max_tokens
        self._base = (base_url or ANTHROPIC_BASE).rstrip("/")
        self._client = make_client(client)

    async def _complete(self, system: str, user: str, *, json_mode: bool) -> tuple[str, Usage]:
        # The Messages API has no JSON mode; the system prompt demands JSON and the caller validates.
        payload = {"model": self.model, "max_tokens": self.max_tokens, "system": system,
                   "messages": [{"role": "user", "content": user}]}
        data = await post_json(self._client, self.name, f"{self._base}/messages",
                               {"x-api-key": self._key, "anthropic-version": "2023-06-01"}, payload)
        try:
            text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        except (KeyError, TypeError, AttributeError):
            raise LLMError("anthropic: unexpected response shape") from None
        u = data.get("usage") or {}
        return text, Usage(u.get("input_tokens", 0), u.get("output_tokens", 0))
