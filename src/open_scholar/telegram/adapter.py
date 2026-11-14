"""Real Telegram Bot API adapter using httpx (long polling; no extra dependency).

Security notes:
* The token lives only in the request URL path; it is never logged. httpx's INFO request
  logging (which prints URLs) is silenced, and error messages are scrubbed of the token.
* Only private chats are served. An optional allow-list restricts who may use the bot.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Iterable

import httpx

from .bot import BotHandler
from .transport import Transport, split_message

log = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)  # would otherwise log URLs containing the token
logging.getLogger("httpcore").setLevel(logging.WARNING)

API = "https://api.telegram.org"


class TelegramError(Exception):
    pass


class TelegramClient:
    def __init__(self, token: str, client: httpx.AsyncClient | None = None, base_url: str = API):
        if not token:
            raise ValueError("Telegram token is required")
        self._token = token
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(40.0, connect=10.0))
        self._base = base_url

    def _scrub(self, text: str) -> str:
        return text.replace(self._token, "<token>")

    async def call(self, method: str, **payload: Any) -> Any:
        try:
            r = await self._client.post(f"{self._base}/bot{self._token}/{method}", json=payload)
        except httpx.HTTPError as e:
            raise TelegramError(f"{method}: network error ({type(e).__name__})") from None
        try:
            data = r.json()
        except ValueError:
            data = {}
        if r.status_code != 200 or not data.get("ok"):
            raise TelegramError(self._scrub(f"{method}: HTTP {r.status_code} {data.get('description', '')}"))
        return data["result"]

    async def aclose(self) -> None:
        await self._client.aclose()


class TelegramTransport(Transport):
    """Sends messages through the real Bot API."""

    def __init__(self, client: TelegramClient):
        self.client = client

    async def send(self, chat_id: int, text: str) -> None:
        for part in split_message(text):
            await self.client.call("sendMessage", chat_id=chat_id, text=part, disable_web_page_preview=True)


class TelegramPoller:
    def __init__(self, client: TelegramClient, handler: BotHandler,
                 allowed_user_ids: Iterable[int] = ()):
        self.client, self.handler = client, handler
        self.allowed = set(allowed_user_ids)
        self.offset = 0

    async def poll_once(self, timeout: int = 30) -> int:
        """Fetch and process one batch of updates. Returns the number of updates seen."""
        updates = await self.client.call("getUpdates", offset=self.offset, timeout=timeout,
                                         allowed_updates=["message"])
        for u in updates:
            self.offset = max(self.offset, u["update_id"] + 1)
            msg = u.get("message") or {}
            sender, chat, text = msg.get("from") or {}, msg.get("chat") or {}, msg.get("text")
            if not text or chat.get("type") != "private" or "id" not in sender:
                continue
            uid = sender["id"]
            if self.allowed and uid not in self.allowed:
                log.info("ignored message from non-allow-listed user")
                continue
            try:
                await self.handler.handle(uid, text, sender.get("first_name"))
            except Exception:
                log.exception("handler failed")  # keep polling
        return len(updates)

    async def run_forever(self) -> None:
        backoff = 1.0
        while True:
            try:
                await self.poll_once()
                backoff = 1.0
            except TelegramError as e:
                log.error("polling error: %s (retry in %.0fs)", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)
