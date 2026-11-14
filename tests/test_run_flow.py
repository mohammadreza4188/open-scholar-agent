"""Integration tests: DB + search mock + eligibility + Persian report + bot, all mocked."""
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from open_scholar.config.profile_loader import load_profile
from open_scholar.core.opportunity import Category, OpportunityRecord
from open_scholar.database import opportunity_repo as orepo
from open_scholar.database.models import EligibilityResult, Opportunity, OpportunityChange, SearchRun
from open_scholar.database.repository import UserRepository
from open_scholar.database.session import init_db, make_engine, make_session_factory
from open_scholar.search.base import SearchResult
from open_scholar.search.mock import MockSearchProvider
from open_scholar.sources.demo import demo_opportunities
from open_scholar.telegram.adapter import TelegramClient, TelegramError, TelegramPoller, TelegramTransport
from open_scholar.telegram.bot import BotHandler
from open_scholar.telegram.transport import MockTransport

EXAMPLE = Path(__file__).parent.parent / "config" / "profile.example.yaml"
NOW = datetime(2026, 11, 14, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def env():
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    sf = make_session_factory(engine)
    t = MockTransport()
    bot = BotHandler(sf, t, providers=[MockSearchProvider()], clock=lambda: NOW)
    return sf, t, bot


def store_profile(sf, tg_id=1, profile=None):
    with sf() as s:
        r = UserRepository(s)
        r.save_profile(r.get_or_create_by_telegram(tg_id), (profile or load_profile(EXAMPLE)).model_dump(mode="json"))
        s.commit()


def seed_demo(sf):
    with sf() as s:
        for o in demo_opportunities(NOW):
            orepo.upsert(s, o, now=NOW)
        s.commit()


def last(t):
    return "\n".join(m for _, m in t.sent)


async def test_run_without_profile(env):
    sf, t, bot = env
    await bot.handle(1, "/run")
    assert "No profile" in last(t)


async def test_run_end_to_end(env):
    sf, t, bot = env
    store_profile(sf)
    seed_demo(sf)
    await bot.handle(1, "/run")
    report = last(t)
    head, rest = report.split("━━ ۵.")
    # actionable: verified, funded, eligible/likely
    assert "[DEMO] Funded MSc in Machine Learning" in head
    assert "[DEMO] Paid AI research internship" in head      # user is enrolled in a Master's
    assert "[DEMO] Direct-entry PhD in NLP" in head          # category B -> Likely Eligible
    assert "احتمالاً واجد شرایط" in head
    # master-required items: Master's not completed -> not actionable
    assert "[DEMO] Second MSc" not in head and "[DEMO] Second MSc" in rest
    assert "[DEMO] PhD requiring Master's" in head.split("در حال حاضر واجد شرایط نیستید")[1]
    # the mock search result was stored UNVERIFIED and is rejected, never actionable
    assert "[MOCK]" not in head and "[MOCK]" in rest
    assert "منابع بررسی‌شده: mock" in rest
    # persistence
    with sf() as s:
        assert s.scalars(select(SearchRun)).first().status == "ok"
        assert len(s.scalars(select(EligibilityResult)).all()) == len(demo_opportunities(NOW)) + 1  # + one deduped mock result


async def test_phd_requiring_masters_rejected_with_reason_when_user_holds_masters(env):
    sf, t, bot = env
    p = load_profile(EXAMPLE)
    for d in p.degrees:
        if d.level.value == "master":
            d.status = type(d.status)("completed")
    store_profile(sf, profile=p)
    seed_demo(sf)
    await bot.handle(1, "/run")
    head, rest = last(t).split("━━ ۵.")
    assert "[DEMO] PhD requiring Master's" not in head
    assert "[DEMO] PhD requiring Master's" in rest
    assert "Requires a completed Master's degree (You already hold one)" in rest


async def test_opportunities_lists_db_rows_with_paging(env):
    sf, t, bot = env
    store_profile(sf)
    seed_demo(sf)
    await bot.handle(1, "/opportunities")
    out = last(t)
    assert "[DEMO] Funded MSc" in out and "صفحه 1/1" in out
    await bot.handle(2, "/opportunities")   # other user without profile sees no data
    assert "No profile" in t.sent[-1][1] and "DEMO" not in t.sent[-1][1]


async def test_run_is_idempotent_and_dedups_search_results(env):
    sf, t, bot = env
    store_profile(sf)
    await bot.handle(1, "/run")
    await bot.handle(1, "/run")
    with sf() as s:
        # 3 priority queries return the same URL: one fingerprint -> one row
        assert len(s.scalars(select(Opportunity)).all()) == 1


async def test_concurrent_runs_blocked(env):
    import asyncio
    sf, t, bot = env
    store_profile(sf)
    await asyncio.gather(bot.handle(1, "/run"), bot.handle(1, "/run"))
    assert sum("already in progress" in m for _, m in t.sent) + sum("گزارش روزانه" in m for _, m in t.sent) >= 1


async def test_failed_search_source_reported(env):
    sf, t, _ = env
    bot = BotHandler(sf, t, providers=[MockSearchProvider(fail=True)], clock=lambda: NOW)
    store_profile(sf)
    await bot.handle(1, "/run")
    assert "منابع ناموفق" in last(t) and "mock failure" in last(t)


def test_upsert_tracks_changes_and_keeps_known_facts():
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    with make_session_factory(engine)() as s:
        base = demo_opportunities(NOW)[0]
        row, created = orepo.upsert(s, base, now=NOW)
        assert created
        later = base.model_copy(update={"deadline": datetime(2027, 6, 1)})
        row, created = orepo.upsert(s, later, now=NOW)
        assert not created and s.scalars(select(OpportunityChange)).one().field == "deadline"
        thin = OpportunityRecord(title=base.title, category=Category.MASTERS, official_url=base.official_url)
        orepo.upsert(s, thin, now=NOW)   # thinner rediscovery must not erase facts
        assert row.funding_type == "full" and row.verification_status == "verified"


# ---- real Telegram adapter, with httpx mocked (no network, no real token) ----
TOKEN = "123456:FAKE-TOKEN"


def tg_client(handler):
    return TelegramClient(TOKEN, httpx.AsyncClient(transport=httpx.MockTransport(handler)))


async def test_transport_sends_split_messages_to_bot_api():
    calls = []

    def h(req: httpx.Request):
        calls.append((req.url.path, req.read()))
        return httpx.Response(200, json={"ok": True, "result": {}})

    await TelegramTransport(tg_client(h)).send(42, "x" * 5000)
    assert len(calls) == 2 and all(p == f"/bot{TOKEN}/sendMessage" for p, _ in calls)


async def test_api_error_does_not_leak_token():
    c = tg_client(lambda r: httpx.Response(401, json={"ok": False, "description": f"bad {TOKEN}"}))
    with pytest.raises(TelegramError) as e:
        await c.call("getMe")
    assert TOKEN not in str(e.value)


async def test_network_error_does_not_leak_token():
    def boom(req):
        raise httpx.ConnectError(f"cannot reach {req.url}")
    with pytest.raises(TelegramError) as e:
        await tg_client(boom).call("getMe")
    assert TOKEN not in str(e.value) and TOKEN not in repr(e.value.__cause__)


async def test_poller_routes_updates_and_enforces_private_chat_and_allowlist(env):
    sf, t, bot = env
    updates = [
        {"update_id": 10, "message": {"text": "/help", "chat": {"type": "private"}, "from": {"id": 1}}},
        {"update_id": 11, "message": {"text": "/help", "chat": {"type": "group"}, "from": {"id": 1}}},
        {"update_id": 12, "message": {"text": "/help", "chat": {"type": "private"}, "from": {"id": 99}}},
    ]
    c = tg_client(lambda r: httpx.Response(200, json={"ok": True, "result": updates}))
    poller = TelegramPoller(c, bot, allowed_user_ids=[1])
    assert await poller.poll_once() == 3
    assert poller.offset == 13 and len(t.sent) == 1 and t.sent[0][0] == 1
