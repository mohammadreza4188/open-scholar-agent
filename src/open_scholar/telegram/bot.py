"""Framework-agnostic command handling.

`BotHandler.handle(telegram_id, text)` is pure application logic; a transport adapter
(mock or real) delivers messages. Every handler resolves the caller's own User row from
their Telegram id, so a user can only ever see their own data.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime, timezone
from time import monotonic
from typing import Callable

from sqlalchemy.orm import Session, sessionmaker

from open_scholar.database import opportunity_repo
from open_scholar.database.repository import UserRepository
from open_scholar.eligibility.engine import EligibilityStatus
from open_scholar.notifications.report import STATUS_FA
from open_scholar.pipeline import NoProfileError, evaluate_all, load_profile, run_for_user
from open_scholar.search.base import SearchProvider
from open_scholar.search.mock import MockSearchProvider

from .transport import Transport

log = logging.getLogger(__name__)

HELP = (
    "دستورات:\n/start /help /profile /run /status /opportunities [صفحه]\n"
    "/pause /resume\n"
    "هنوز پیاده‌سازی نشده: /edit_profile /settings /sources /deadlines"
)
NOT_IMPLEMENTED = "این قابلیت هنوز پیاده‌سازی نشده است. (Not implemented yet.)"
NO_PROFILE = "پروفایلی ثبت نشده است. No profile yet (load one with `open-scholar load-profile`)."
PAGE_SIZE = 8


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
                 rate_limiter: RateLimiter | None = None,
                 providers: list[SearchProvider] | None = None,
                 llm=None, fetcher=None, max_pages: int = 5, cost_fn=lambda i, o: 0.0,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.sf, self.transport = session_factory, transport
        self.limiter = rate_limiter or RateLimiter()
        self.providers = providers if providers is not None else [MockSearchProvider()]
        self.clock = clock
        self.llm, self.fetcher, self.max_pages, self.cost_fn = llm, fetcher, max_pages, cost_fn
        self._run_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def handle(self, telegram_id: int, text: str, name: str | None = None) -> None:
        if not self.limiter.allow(telegram_id):
            await self.transport.send(telegram_id, "Too many requests, slow down.")
            return
        parts = text.strip().split()
        cmd = parts[0].lower().split("@")[0] if parts else ""
        arg = parts[1] if len(parts) > 1 else ""
        with self.sf() as s:
            repo = UserRepository(s)
            user = repo.get_or_create_by_telegram(telegram_id, name)
            if cmd == "/run":
                reply = await self._run(s, user, telegram_id)
            elif cmd == "/opportunities":
                reply = self._opportunities(s, user, arg)
            else:
                reply = self._simple(cmd, user)
            s.commit()
        await self.transport.send(telegram_id, reply)

    async def _run(self, s: Session, user, telegram_id: int) -> str:
        lock = self._run_locks[telegram_id]
        if lock.locked():  # prevent duplicate concurrent runs/reports for one user
            return "یک اجرا در حال انجام است. A run is already in progress."
        async with lock:
            try:
                return await run_for_user(s, user, self.providers, self.clock(), llm=self.llm,
                                          fetcher=self.fetcher, max_pages=self.max_pages,
                                          cost_fn=self.cost_fn)
            except NoProfileError:
                return NO_PROFILE
            except Exception:  # never leak internals to the chat
                log.exception("run failed for user %s", user.id)
                return "اجرا با خطا مواجه شد. The run failed; see server logs."

    def _opportunities(self, s: Session, user, arg: str) -> str:
        try:
            profile = load_profile(user)
        except NoProfileError:
            return NO_PROFILE
        page = int(arg) if arg.isdigit() and int(arg) > 0 else 1
        items = evaluate_all(s, user, profile, self.clock())
        if not items:
            return "فرصتی ذخیره نشده است. No saved opportunities (try /run)."
        pages = (len(items) + PAGE_SIZE - 1) // PAGE_SIZE
        page = min(page, pages)
        lines = [f"فرصت‌های ذخیره‌شده — صفحه {page}/{pages}"]
        for row, rec, dec in items[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]:
            lines.append(f"{row.id}. [{rec.category.value}] {rec.title} — {rec.organization or 'نامشخص'}\n"
                         f"   تأیید: {rec.verification_status.value} | شرایط: {STATUS_FA[dec.status]}")
        if page < pages:
            lines.append(f"/opportunities {page + 1} برای صفحهٔ بعد")
        return "\n".join(lines)

    def _simple(self, cmd: str, user) -> str:
        if cmd == "/start":
            return "به OpenScholar Agent خوش آمدید.\n" + HELP
        if cmd == "/help":
            return HELP
        if cmd == "/profile":
            if user.profile is None:
                return NO_PROFILE
            p = load_profile(user)
            hi = p.highest_completed.value if p.highest_completed else "none"
            enrolled = [d.level.value for d in p.degrees if d.status.value == "in_progress"]
            return (f"Highest completed degree: {hi}\nIn progress: {', '.join(enrolled) or '-'}\n"
                    f"Interests: {', '.join(p.research_interests) or '-'}")
        if cmd == "/status":
            state = "paused" if user.paused else "active"
            return f"Status: {state}\nTimezone: {user.timezone}\nReport time: {user.report_time}"
        if cmd == "/pause":
            user.paused = True
            return "گزارش‌های خودکار متوقف شد. Scheduled reports paused."
        if cmd == "/resume":
            user.paused = False
            return "گزارش‌ها ادامه می‌یابد. Reports resumed."
        if cmd in {"/edit_profile", "/settings", "/sources", "/deadlines"}:
            return NOT_IMPLEMENTED
        return "Unknown command. /help"
