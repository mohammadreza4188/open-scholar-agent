"""Local entry point.

  open-scholar init-db
  open-scholar load-profile config/profile.example.yaml --telegram-id <ID>
  open-scholar seed-demo            # clearly-labelled DEMO opportunities (not real)
  open-scholar config               # show what is configured (no secrets printed)
  open-scholar test-search          # one tiny query per configured search provider
  open-scholar test-llm             # one tiny call to the configured LLM
  open-scholar chat                 # simulated Telegram on stdin (mock transport)
  open-scholar bot                  # real Telegram long polling (needs TELEGRAM_BOT_TOKEN)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone

from open_scholar.config.profile_loader import load_profile
from open_scholar.config.settings import Settings
from open_scholar.database import opportunity_repo
from open_scholar.database.repository import UserRepository
from open_scholar.database.session import init_db, make_engine, make_session_factory
from open_scholar.llm.factory import LLMConfigError, estimate_cost, get_llm, resolve_provider_name
from open_scholar.search.registry import build_providers
from open_scholar.sources.demo import demo_opportunities
from open_scholar.telegram.bot import BotHandler
from open_scholar.telegram.transport import MockTransport
from open_scholar.verification.fetch import PageFetcher


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="open-scholar")
    ap.add_argument("command", choices=["chat", "init-db", "load-profile", "seed-demo", "bot",
                                        "test-llm", "test-search", "config"])
    ap.add_argument("path", nargs="?", help="profile file (load-profile)")
    ap.add_argument("--telegram-id", type=int, default=1)
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):  # Persian text on Windows consoles
        stream.reconfigure(encoding="utf-8", errors="replace")

    settings = Settings.from_env()
    logging.basicConfig(level=settings.log_level)

    if args.command == "config":
        print(settings)
        print("search providers:", [p.name for p in build_providers(settings)])
        print("llm provider:", resolve_provider_name(settings) or "disabled (rules-only extraction)")
        return 0
    if args.command == "test-search":
        return asyncio.run(_test_search(settings))
    if args.command == "test-llm":
        return asyncio.run(_test_llm(settings))

    engine = make_engine(settings.database_url)
    init_db(engine)
    sf = make_session_factory(engine)

    if args.command == "init-db":
        print("Database initialised.")
    elif args.command == "load-profile":
        if not args.path:
            ap.error("load-profile needs a profile file path")
        profile = load_profile(args.path)  # validates
        with sf() as s:
            r = UserRepository(s)
            r.save_profile(r.get_or_create_by_telegram(args.telegram_id), profile.model_dump(mode="json"))
            s.commit()
        print(f"Profile stored for telegram id {args.telegram_id}.")
    elif args.command == "seed-demo":
        with sf() as s:
            created = sum(opportunity_repo.upsert(s, o)[1] for o in demo_opportunities(datetime.now(timezone.utc)))
            s.commit()
        print(f"Seeded {created} new DEMO opportunities (fake, example.org only).")
    elif args.command == "chat":
        try:
            handler = _make_handler(settings, sf, MockTransport(echo=True))
        except LLMConfigError as e:
            print(f"[config] {e}")
            return 2
        print(f"Mock Telegram chat (user id {args.telegram_id}). Ctrl+C to quit.")
        try:
            while True:
                asyncio.run(handler.handle(args.telegram_id, input("> ")))
        except (KeyboardInterrupt, EOFError):
            print()
    elif args.command == "bot":
        if not settings.telegram_bot_token:
            print("TELEGRAM_BOT_TOKEN is not set (put it in .env). Use `chat` for the mock bot.")
            return 2
        return asyncio.run(_run_bot(settings, sf))
    return 0


def _make_handler(settings: Settings, sf, transport) -> BotHandler:
    """Real search/LLM when configured in .env, otherwise mock search + rule-based extraction."""
    llm = get_llm(settings)  # raises LLMConfigError on bad config
    providers = build_providers(settings)
    live = any(p.name != "mock" for p in providers)
    print(f"search: {[p.name for p in providers]} | "
          f"extraction: {('LLM ' + llm.name + '/' + llm.model) if llm else 'rules'} | "
          f"page fetching: {'on' if live else 'off (mock search only)'}")
    return BotHandler(sf, transport, providers=providers, llm=llm,
                      fetcher=PageFetcher() if live else None, max_pages=settings.max_pages_per_run,
                      cost_fn=lambda i, o: estimate_cost(settings, i, o))


async def _test_search(settings: Settings) -> int:
    from open_scholar.search.base import SearchError
    rc = 0
    for p in build_providers(settings):
        try:
            res = await p.search("funded master's artificial intelligence scholarship", max_results=3)
            print(f"[ok] {p.name}: {len(res)} results")
            for r in res:
                print("   -", r.title[:80], "|", r.url)
        except SearchError as e:
            print(f"[fail] {p.name}: {e}")
            rc = 1
    return rc


async def _test_llm(settings: Settings) -> int:
    from open_scholar.llm.base import LLMError
    try:
        llm = get_llm(settings)
    except LLMConfigError as e:
        print(f"[config] {e}")
        return 2
    if llm is None:
        print("LLM disabled (no key configured, or OSA_LLM_PROVIDER=none).")
        return 0
    try:
        await llm.test_connection()
    except LLMError as e:
        print(f"[fail] {llm.name}/{llm.model}: {e}")
        return 1
    u = llm.totals()
    print(f"[ok] {llm.name}/{llm.model} reachable (tokens in/out: {u.input_tokens}/{u.output_tokens})")
    return 0


async def _run_bot(settings: Settings, sf) -> int:
    from open_scholar.telegram.adapter import TelegramClient, TelegramError, TelegramPoller, TelegramTransport
    client = TelegramClient(settings.telegram_bot_token)
    try:
        me = await client.call("getMe")
        print(f"Connected as @{me.get('username')}. Polling... Ctrl+C to stop.")
        handler = _make_handler(settings, sf, TelegramTransport(client))
        await TelegramPoller(client, handler, settings.telegram_allowed_user_ids).run_forever()
    except LLMConfigError as e:
        print(f"[config] {e}")
        return 2
    except TelegramError as e:
        print(f"Telegram error: {e}")
        return 1
    except KeyboardInterrupt:
        pass
    finally:
        await client.aclose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
