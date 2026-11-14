# Progress

Legend: **Tested** = automated tests pass (HTTP mocked) · **Manual** = run by hand against a real service ·
**Untested live** = implemented, never called against the real service · **Planned**.

## Phase 1 - MVP (done)
- Profile schema (completed vs in-progress degrees), SQLite models, deterministic eligibility engine (scenarios A-H),
  match score, Persian daily report, `/run` + `/opportunities`, duplicate detection, change tracking. **Tested.**
- Real Telegram adapter (httpx long polling). **Tested** with a mocked transport; **Manual** - the maintainer
  confirmed `/start` worked against the real Bot API (through a VPN).

## Phase 2 - Multi-LLM (code complete, not yet run against real APIs)
| Piece | Status |
|---|---|
| OpenAI adapter (`llm/openai_provider.py`), also serves any OpenAI-compatible endpoint via `OSA_LLM_BASE_URL` | Tested (mock) / **Untested live** |
| Anthropic adapter (default model `claude-haiku-5-5`) | Tested (mock) / **Untested live** |
| Gemini adapter | Tested (mock) / **Untested live** |
| Pydantic-validated structured output (`ExtractedRequirements`), JSON repair of code fences, schema errors -> `LLMError` | Tested |
| Provider selection (`OSA_LLM_PROVIDER=auto/none/<name>`), `open-scholar test-llm` connection test | Tested (selection) / **Untested live** |
| Usage + estimated cost -> `provider_usage` table (cost needs `OSA_LLM_PRICE_*`; otherwise 0.0) | Tested |

Design decisions
- **httpx, not vendor SDKs**: three small adapters share one error/prompt/validation layer, keys travel only in
  headers (never URLs), errors never echo keys, and tests mock one transport. Trade-off: new vendor features
  (e.g. native structured-output modes beyond JSON mode) must be added by hand.
- **No default model is assumed** for OpenAI/Gemini/compatible (model names change); set `OSA_LLM_MODEL`.
- **Prompt-injection controls**: page text is wrapped in `<untrusted_page>` tags with closing tags neutralised; the
  system prompt says it is data; the user's profile is *never* sent for extraction; output is schema-validated.
- **Grounding** (`verification/grounding.py`): every extracted claim needs a verbatim quote that exists in the page
  (and degree claims must name the degree level) or it is reset to "unknown". This applies to LLM *and* rules output.
- LLM failure of any kind falls back to the rule extractor; `/run` reports which method was used.

## Phase 3 (started) - real search + page verification
| Piece | Status |
|---|---|
| Brave Search adapter, Tavily adapter (`search/`), documented `ProviderInfo` | Tested (mock) / **Untested live** |
| Polite page fetcher: robots.txt, SSRF guard (re-checked on redirects), size/content-type limits | Tested |
| Rule-based extractor (conservative; "fully funded" wording alone is never trusted) | Tested |
| Enrichment in `/run`: fetch up to `OSA_MAX_PAGES_PER_RUN` unverified pages, extract, store evidence rows, set status | Tested |
| Engine: failed requirement from a non-official source -> Uncertain (never a hard rejection) | Tested |

Known limitations
- "Official source" is a **domain heuristic** (`.edu`, `.gov`, `.ac.xx`, `.edu.xx`, `.go.xx`). Company and many
  non-English institutional domains are not recognised and stay Unverified/Uncertain.
- Pages that need JavaScript, logins or PDFs are not read (reported as failed fetches).
- Search results are discovery hints; the category of a result comes from the query that found it and may be wrong.
- Rule extractor is English-only and intentionally silent on ambiguity.
- A failed fetch is retried on later runs (bounded by `OSA_MAX_PAGES_PER_RUN`); a successful one is not re-checked
  yet (no freshness re-check / change detection for pages).
- Provider pricing, rate limits and terms are linked, not asserted - check each provider's current terms.
- Database still uses `create_all` (no migrations): delete `data/open_scholar.db` after pulling schema changes.

## Not started
Scheduler / daily push, `/edit_profile`, `/settings`, `/sources`, `/deadlines`, strict date parsing for
"before enrollment" (Phase 3 TODO in the engine), Docker, GitHub Actions, application assistant.

## Try it
```
python -m open_scholar.cli config        # what is configured (no secrets printed)
python -m open_scholar.cli test-search   # needs BRAVE_API_KEY and/or TAVILY_API_KEY
python -m open_scholar.cli test-llm      # needs a provider key (+ OSA_LLM_MODEL except for anthropic)
python -m open_scholar.cli bot
```
In `.env` set `OSA_LLM_PROVIDER=auto` (or a provider name); `none` disables the LLM.
