"""OpenAI Chat Completions adapter (also serves any OpenAI-compatible endpoint via base_url)."""
from __future__ import annotations

import httpx

from ._http import make_client, post_json
from .base import LLMError, LLMProvider, Usage

OPENAI_BASE = "https://api.openai.com/v1"


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str | None = None,
                 client: httpx.AsyncClient | None = None, name: str | None = None):
        super().__init__()
        if not api_key:
            raise ValueError("API key required")
        self._key, self.model = api_key, model
        self._base = (base_url or OPENAI_BASE).rstrip("/")
        self._client = make_client(client)
        if name:
            self.name = name

    async def _complete(self, system: str, user: str, *, json_mode: bool) -> tuple[str, Usage]:
        payload: dict = {"model": self.model,
                         "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = await post_json(self._client, self.name, f"{self._base}/chat/completions",
                               {"Authorization": f"Bearer {self._key}"}, payload)
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise LLMError(f"{self.name}: unexpected response shape") from None
        u = data.get("usage") or {}
        return text, Usage(u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
