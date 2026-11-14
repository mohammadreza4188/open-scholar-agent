"""Application settings loaded from environment (.env). No secrets in code."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _opt(name: str) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or None


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///data/open_scholar.db"
    log_level: str = "INFO"
    telegram_bot_token: str | None = None
    telegram_allowed_user_ids: tuple[int, ...] = ()
    brave_api_key: str | None = None
    tavily_api_key: str | None = None
    llm_provider: str = "none"
    llm_model: str | None = None

    @classmethod
    def from_env(cls, load_dotenv_file: bool = True) -> "Settings":
        if load_dotenv_file:
            load_dotenv()
        return cls(
            database_url=os.environ.get("OSA_DATABASE_URL", cls.database_url),
            log_level=os.environ.get("OSA_LOG_LEVEL", cls.log_level),
            telegram_bot_token=_opt("TELEGRAM_BOT_TOKEN"),
            telegram_allowed_user_ids=tuple(
                int(x) for x in os.environ.get("TELEGRAM_ALLOWED_USER_IDS", "").replace(" ", "").split(",") if x),
            brave_api_key=_opt("BRAVE_API_KEY"),
            tavily_api_key=_opt("TAVILY_API_KEY"),
            llm_provider=os.environ.get("OSA_LLM_PROVIDER", "none").lower(),
            llm_model=_opt("OSA_LLM_MODEL"),
        )

    def __repr__(self) -> str:  # never leak secrets in logs
        return (
            f"Settings(database_url={self.database_url!r}, "
            f"telegram={'set' if self.telegram_bot_token else 'unset'}, "
            f"brave={'set' if self.brave_api_key else 'unset'}, "
            f"tavily={'set' if self.tavily_api_key else 'unset'}, "
            f"llm_provider={self.llm_provider!r})"
        )
