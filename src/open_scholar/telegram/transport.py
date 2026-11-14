"""Message transport abstraction. MockTransport lets the bot run with no token."""
from __future__ import annotations

from abc import ABC, abstractmethod

TELEGRAM_MAX_LEN = 4096


def split_message(text: str, limit: int = TELEGRAM_MAX_LEN) -> list[str]:
    """Split on line boundaries so each chunk fits Telegram's length limit."""
    chunks: list[str] = []
    cur = ""
    for line in text.split("\n"):
        while len(line) > limit:  # pathological single line
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if len(cur) + len(line) + (1 if cur else 0) > limit:
            chunks.append(cur)
            cur = line
        else:
            cur = f"{cur}\n{line}" if cur else line
    if cur:
        chunks.append(cur)
    return chunks


class Transport(ABC):
    @abstractmethod
    async def send(self, chat_id: int, text: str) -> None: ...


class MockTransport(Transport):
    """Records messages instead of sending. Never contacts Telegram."""

    def __init__(self, echo: bool = False):
        self.sent: list[tuple[int, str]] = []
        self.echo = echo

    async def send(self, chat_id: int, text: str) -> None:
        for part in split_message(text):
            self.sent.append((chat_id, part))
            if self.echo:
                print(f"[mock-telegram -> {chat_id}] {part}")
