"""Google Gemini generateContent adapter (httpx). The key goes in a header, never in the URL."""
from __future__ import annotations

import httpx

from ._http import make_client, post_json
from .base import LLMError, LLMProvider, Usage

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, base_url: str | None = None,
                 client: httpx.AsyncClient | None = None):
        super().__init__()
        if not api_key:
            raise ValueError("API key required")
        self._key, self.model = api_key, model
        self._base = (base_url or GEMINI_BASE).rstrip("/")
        self._client = make_client(client)

    async def _complete(self, system: str, user: str, *, json_mode: bool) -> tuple[str, Usage]:
        payload: dict = {"systemInstruction": {"parts": [{"text": system}]},
                         "contents": [{"role": "user", "parts": [{"text": user}]}]}
        if json_mode:
            payload["generationConfig"] = {"responseMimeType": "application/json"}
        data = await post_json(self._client, self.name, f"{self._base}/models/{self.model}:generateContent",
                               {"x-goog-api-key": self._key}, payload)
        try:
            text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError, TypeError, AttributeError):
            raise LLMError("gemini: unexpected response shape (blocked or empty)") from None
        u = data.get("usageMetadata") or {}
        return text, Usage(u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0))
