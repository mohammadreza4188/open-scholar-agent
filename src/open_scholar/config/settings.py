"""Application settings loaded from environment (.env). No secrets in code."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _opt(name: str) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or None


def _float(name: str) -> float | None:
    v = _opt(name)
    return float(v) if v else None


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///data/open_scholar.db"
    log_level: str = "INFO"
    telegram_bot_token: str | None = None
    telegram_allowed_user_ids: tuple[int, ...] = ()
    brave_api_key: str | None = None
    tavily_api_key: str | None = None
    # LLM: "auto" (first provider with a key), "none" (disabled), or an explicit provider name
    llm_provider: str = "auto"
    llm_model: str | None = None
    llm_base_url: str | None = None          # for openai_compatible / proxies
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    llm_price_in_per_mtok: float | None = None   # USD per million input tokens (for cost estimates)
    llm_price_out_per_mtok: float | None = None
    max_pages_per_run: int = 5

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
            llm_provider=(_opt("OSA_LLM_PROVIDER") or "auto").lower(),
            llm_model=_opt("OSA_LLM_MODEL"),
            llm_base_url=_opt("OSA_LLM_BASE_URL"),
            openai_api_key=_opt("OPENAI_API_KEY"),
            anthropic_api_key=_opt("ANTHROPIC_API_KEY"),
            gemini_api_key=_opt("GEMINI_API_KEY"),
            llm_price_in_per_mtok=_float("OSA_LLM_PRICE_IN_PER_MTOK"),
            llm_price_out_per_mtok=_float("OSA_LLM_PRICE_OUT_PER_MTOK"),
            max_pages_per_run=int(os.environ.get("OSA_MAX_PAGES_PER_RUN", cls.max_pages_per_run)),
        )

    def __repr__(self) -> str:  # never leak secrets in logs
        def s(v): return "set" if v else "unset"
        return (
            f"Settings(database_url={self.database_url!r}, telegram={s(self.telegram_bot_token)}, "
            f"brave={s(self.brave_api_key)}, tavily={s(self.tavily_api_key)}, "
            f"openai={s(self.openai_api_key)}, anthropic={s(self.anthropic_api_key)}, "
            f"gemini={s(self.gemini_api_key)}, llm_provider={self.llm_provider!r})"
        )
