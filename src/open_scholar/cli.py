"""Local entry point: `open-scholar chat` simulates Telegram on stdin (mock transport)."""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from open_scholar.config.settings import Settings
from open_scholar.database.session import init_db, make_engine, make_session_factory
from open_scholar.telegram.bot import BotHandler
from open_scholar.telegram.transport import MockTransport


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="open-scholar")
    ap.add_argument("command", choices=["chat", "init-db"])
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):  # Persian text on Windows consoles
        stream.reconfigure(encoding="utf-8", errors="replace")

    settings = Settings.from_env()
    logging.basicConfig(level=settings.log_level)
    engine = make_engine(settings.database_url)
    init_db(engine)
    if args.command == "init-db":
        print("Database initialised.")
        return 0

    if settings.telegram_bot_token:
        print("Token found, but the real Telegram adapter is not implemented yet; using mock transport.")
    handler = BotHandler(make_session_factory(engine), MockTransport(echo=True))
    print("Mock Telegram chat (user id 1). Type commands, Ctrl+C to quit.")
    try:
        while True:
            asyncio.run(handler.handle(1, input("> ")))
    except (KeyboardInterrupt, EOFError):
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
