"""Choose an LLM provider from settings. None means 'LLM disabled' (rules-only mode)."""
from __future__ import annotations

import httpx

from open_scholar.config.settings import Settings

from .anthropic_provider import AnthropicProvider
from .base import LLMProvider
from .gemini_provider import GeminiProvider
from .mock import MockLLMProvider
from .openai_provider import OpenAIProvider

PROVIDERS = ("openai", "anthropic", "gemini", "openai_compatible")


class LLMConfigError(Exception):
    pass


def resolve_provider_name(s: Settings) -> str | None:
    p = s.llm_provider
    if p in ("none", "off", "disabled"):
        return None
    if p == "auto":
        for name, key in (("openai", s.openai_api_key), ("anthropic", s.anthropic_api_key),
                          ("gemini", s.gemini_api_key)):
            if key:
                return name
        return "openai_compatible" if (s.llm_base_url and s.openai_api_key) else None
    return p


def get_llm(s: Settings, client: httpx.AsyncClient | None = None) -> LLMProvider | None:
    name = resolve_provider_name(s)
    if name is None:
        return None
    if name == "mock":
        return MockLLMProvider()

    def need(key: str | None, env: str) -> str:
        if not key:
            raise LLMConfigError(f"OSA_LLM_PROVIDER={name} but {env} is not set")
        return key

    def need_model() -> str:
        if not s.llm_model:
            raise LLMConfigError(f"set OSA_LLM_MODEL for provider {name!r} (no default model is assumed)")
        return s.llm_model

    if name == "openai":
        return OpenAIProvider(need(s.openai_api_key, "OPENAI_API_KEY"), need_model(), s.llm_base_url, client)
    if name == "openai_compatible":
        if not s.llm_base_url:
            raise LLMConfigError("openai_compatible needs OSA_LLM_BASE_URL")
        return OpenAIProvider(need(s.openai_api_key, "OPENAI_API_KEY"), need_model(), s.llm_base_url, client,
                              name="openai_compatible")
    if name == "anthropic":
        return AnthropicProvider(need(s.anthropic_api_key, "ANTHROPIC_API_KEY"), s.llm_model, s.llm_base_url, client)
    if name == "gemini":
        return GeminiProvider(need(s.gemini_api_key, "GEMINI_API_KEY"), need_model(), s.llm_base_url, client)
    raise LLMConfigError(f"unknown LLM provider {name!r}; choose one of {PROVIDERS}, 'auto' or 'none'")


def estimate_cost(s: Settings, input_tokens: int, output_tokens: int) -> float:
    """USD estimate from user-supplied prices (OSA_LLM_PRICE_*); 0.0 when prices are not configured."""
    if s.llm_price_in_per_mtok is None or s.llm_price_out_per_mtok is None:
        return 0.0
    return (input_tokens * s.llm_price_in_per_mtok + output_tokens * s.llm_price_out_per_mtok) / 1_000_000
