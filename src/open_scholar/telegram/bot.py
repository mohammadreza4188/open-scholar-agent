"""Framework-agnostic command handling.

`BotHandler.handle(telegram_id, text)` is pure application logic; a real Telegram
library adapter (python-telegram-bot, Phase 1b) just forwards updates to it.
Every handler resolves the caller's own User row from their Telegram id, so a
user can only ever see their own data.
"""
from __future__ import annotations

import logging
from collections import defaultdict, deque
from time import monotonic

from sqlalchemy.orm import Session, sessionmaker

from open_scholar.core.profile import UserProfile
from open_scholar.database.repository import UserRepository

from .transport import Transport

log = logging.getLogger(__name__)

HELP = (
    "دستورات:\n/start /help /profile /edit_profile /run /status\n"
    "/settings /sources /opportunities /deadlines /pause /resume\n"
    "(commands marked later are not implemented yet)"
)
NOT_IMPLEMENTED = "این قابلیت هنوز پیاده‌سازی نشده است. (Not implemented yet.)"


class RateLimiter:
    def __init__(self, max_calls: int = 20, per_seconds: float = 60.0):
        self.max, self.window = max_calls, per_seconds
        self._calls: dict[int, deque[float]] = defaultdict(deque)

    def allow(self, key: int) -> bool:
        now, q = monotonic(), self._calls[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max:
            return False
        q.append(now)
        return True


class BotHandler:
    def __init__(self, session_factory: sessionmaker[Session], transport: Transport,
                 rate_limiter: RateLimiter | None = None):
        self.sf, self.transport = session_factory, transport
        self.limiter = rate_limiter or RateLimiter()

    async def handle(self, telegram_id: int, text: str, name: str | None = None) -> None:
        if not self.limiter.allow(telegram_id):
            await self.transport.send(telegram_id, "Too many requests, slow down.")
            return
        cmd = text.strip().split()[0].lower().split("@")[0] if text.strip() else ""
        with self.sf() as s:
            repo = UserRepository(s)
            user = repo.get_or_create_by_telegram(telegram_id, name)
            reply = self._dispatch(cmd, user, repo)
            s.commit()
        await self.transport.send(telegram_id, reply)

    def _dispatch(self, cmd: str, user, repo: UserRepository) -> str:
        if cmd == "/start":
            return "به OpenScholar Agent خوش آمدید.\n" + HELP
        if cmd == "/help":
            return HELP
        if cmd == "/profile":
            if user.profile is None:
                return "پروفایلی ثبت نشده است. No profile yet."
            p = UserProfile.model_validate(user.profile.data)
            hi = p.highest_completed.value if p.highest_completed else "none"
            return f"Highest completed degree: {hi}\nInterests: {', '.join(p.research_interests) or '-'}"
        if cmd == "/status":
            state = "paused" if user.paused else "active"
            return f"Status: {state}\nTimezone: {user.timezone}\nReport time: {user.report_time}"
        if cmd == "/pause":
            user.paused = True
            return "گزارش‌ها متوقف شد. Reports paused."
        if cmd == "/resume":
            user.paused = False
            return "گزارش‌ها ادامه می‌یابد. Reports resumed."
        if cmd in {"/edit_profile", "/run", "/settings", "/sources", "/opportunities", "/deadlines"}:
            return NOT_IMPLEMENTED
        return "Unknown command. /help"
