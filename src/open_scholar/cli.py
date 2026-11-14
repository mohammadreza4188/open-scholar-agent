"""Local entry point.

  open-scholar init-db
  open-scholar load-profile --telegram-id 1 config/profile.example.yaml
  open-scholar seed-demo            # clearly-labelled DEMO opportunities (not real)
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
from open_scholar.search.registry import build_providers
from open_scholar.sources.demo import demo_opportunities
from open_scholar.telegram.bot import BotHandler
from open_scholar.telegram.transport import MockTransport


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="open-scholar")
    ap.add_argument("command", choices=["chat", "init-db", "load-profile", "seed-demo", "bot"])
    ap.add_argument("path", nargs="?", help="profile file (load-profile)")
    ap.add_argument("--telegram-id", type=int, default=1)
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):  # Persian text on Windows consoles
        stream.reconfigure(encoding="utf-8", errors="replace")

    settings = Settings.from_env()
    logging.basicConfig(level=settings.log_level)
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
        handler = BotHandler(sf, MockTransport(echo=True), providers=build_providers(settings))
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


async def _run_bot(settings: Settings, sf) -> int:
    from open_scholar.telegram.adapter import TelegramClient, TelegramError, TelegramPoller, TelegramTransport
    client = TelegramClient(settings.telegram_bot_token)
    try:
        me = await client.call("getMe")
        print(f"Connected as @{me.get('username')}. Polling... Ctrl+C to stop.")
        handler = BotHandler(sf, TelegramTransport(client), providers=build_providers(settings))
        await TelegramPoller(client, handler, settings.telegram_allowed_user_ids).run_forever()
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
