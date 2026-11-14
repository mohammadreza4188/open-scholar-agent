from pathlib import Path

from open_scholar.config.profile_loader import load_profile
from open_scholar.config.settings import Settings
from open_scholar.database.repository import UserRepository
from open_scholar.database.session import init_db, make_engine, make_session_factory
from open_scholar.llm.mock import get_llm
from open_scholar.search.mock import MockSearchProvider
from open_scholar.search.registry import build_providers, search_all
from open_scholar.telegram.bot import BotHandler, RateLimiter
from open_scholar.telegram.transport import MockTransport, split_message

EXAMPLE = Path(__file__).parent.parent / "config" / "profile.example.yaml"


async def test_search_reports_failures_and_mock_fallback():
    assert build_providers(Settings())[0].name == "mock"
    results, checked, failed = await search_all([MockSearchProvider(), MockSearchProvider(fail=True)], "ai")
    assert len(results) == 1 and checked == ["mock"] and "mock" in failed


def test_llm_optional():
    assert get_llm("none") is None


def test_settings_repr_hides_secrets():
    assert "abc123" not in repr(Settings(telegram_bot_token="abc123"))


def test_split_message_respects_limit():
    parts = split_message("\n".join(["x" * 100] * 100), limit=1000)
    assert all(len(p) <= 1000 for p in parts) and len(parts) > 1


async def test_bot_commands_and_user_isolation():
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    sf = make_session_factory(engine)
    t = MockTransport()
    bot = BotHandler(sf, t)
    with sf() as s:
        repo = UserRepository(s)
        u = repo.get_or_create_by_telegram(1)
        repo.save_profile(u, load_profile(EXAMPLE).model_dump(mode="json"))
        s.commit()
    await bot.handle(1, "/profile")
    await bot.handle(2, "/profile")  # different user must not see user 1's data
    await bot.handle(1, "/pause")
    await bot.handle(1, "/status")
    assert "bachelor" in t.sent[0][1]
    assert "No profile" in t.sent[1][1]
    assert "paused" in t.sent[3][1]


async def test_rate_limit():
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    t = MockTransport()
    bot = BotHandler(make_session_factory(engine), t, RateLimiter(max_calls=1))
    await bot.handle(1, "/help")
    await bot.handle(1, "/help")
    assert "Too many" in t.sent[-1][1]
