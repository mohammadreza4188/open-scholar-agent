"""Search adapters, page fetcher and the enriched /run flow - HTTP fully mocked."""
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from open_scholar.config.profile_loader import load_profile
from open_scholar.config.settings import Settings
from open_scholar.database.models import Opportunity, OpportunityEvidence, ProviderUsage
from open_scholar.database.repository import UserRepository
from open_scholar.database.session import init_db, make_engine, make_session_factory
from open_scholar.llm.mock import MockLLMProvider
from open_scholar.search.base import SearchError, SearchResult
from open_scholar.search.brave import BraveSearchProvider
from open_scholar.search.mock import MockSearchProvider
from open_scholar.search.registry import build_providers
from open_scholar.search.tavily import TavilySearchProvider
from open_scholar.telegram.bot import BotHandler
from open_scholar.telegram.transport import MockTransport
from open_scholar.verification.extract import is_probably_official
from open_scholar.verification.fetch import FetchError, PageFetcher, html_to_text

KEY = "search-SECRET-key"
NOW = datetime(2026, 11, 14, 8, 0, tzinfo=timezone.utc)
EXAMPLE = Path(__file__).parent.parent / "config" / "profile.example.yaml"


def client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# ---------------------------------------------------------------- search adapters
async def test_brave_request_and_parsing():
    seen = {}

    def h(req: httpx.Request):
        seen["req"] = req
        return httpx.Response(200, json={"web": {"results": [
            {"title": "A <strong>MSc</strong>", "url": "https://uni.edu/a", "description": "d <b>x</b>"},
            {"title": "bad scheme", "url": "javascript:alert(1)"},
            {"title": "no url"},
        ]}})

    res = await BraveSearchProvider(KEY, client(h)).search("ai msc", max_results=5)
    assert [r.url for r in res] == ["https://uni.edu/a"]
    assert res[0].title == "A MSc" and res[0].snippet == "d x" and res[0].provider == "brave"
    r = seen["req"]
    assert r.headers["x-subscription-token"] == KEY and KEY not in str(r.url)
    assert r.url.params["q"] == "ai msc" and r.url.params["count"] == "5"


async def test_tavily_request_and_parsing():
    seen = {}

    def h(req):
        seen["req"], seen["body"] = req, json.loads(req.read())
        return httpx.Response(200, json={"results": [{"title": "T", "url": "https://x.org/p", "content": "c" * 900}]})

    res = await TavilySearchProvider(KEY, client(h)).search("q", max_results=3)
    assert res[0].url == "https://x.org/p" and len(res[0].snippet) == 500
    assert seen["req"].headers["authorization"] == f"Bearer {KEY}" and KEY not in json.dumps(seen["body"])
    assert seen["body"]["max_results"] == 3


@pytest.mark.parametrize("cls", [BraveSearchProvider, TavilySearchProvider])
@pytest.mark.parametrize("status,msg", [(401, "authentication"), (429, "rate limited"), (503, "HTTP 503")])
async def test_search_http_errors(cls, status, msg):
    with pytest.raises(SearchError, match=msg) as e:
        await cls(KEY, client(lambda r: httpx.Response(status, text=KEY))).search("q")
    assert KEY not in str(e.value)


@pytest.mark.parametrize("cls", [BraveSearchProvider, TavilySearchProvider])
async def test_search_network_and_bad_json(cls):
    def boom(req):
        raise httpx.ConnectTimeout(f"timeout {req.url}")
    with pytest.raises(SearchError, match="network error"):
        await cls(KEY, client(boom)).search("q")
    with pytest.raises(SearchError, match="not JSON"):
        await cls(KEY, client(lambda r: httpx.Response(200, text="<html>"))).search("q")


def test_registry_uses_real_providers_when_keys_exist_else_mock():
    assert [p.name for p in build_providers(Settings())] == ["mock"]
    assert [p.name for p in build_providers(Settings(brave_api_key="k", tavily_api_key="k"))] == ["brave", "tavily"]
    assert BraveSearchProvider.info.terms_url and TavilySearchProvider.info.requires_api_key


# ---------------------------------------------------------------- fetcher
PUBLIC = "93.184.216.34"


async def public_resolver(host):
    return [PUBLIC]


def fetcher(handler, **kw):
    return PageFetcher(client(handler), resolver=kw.pop("resolver", public_resolver), **kw)


def page_handler(body="<html><body><p>Hello world</p></body></html>", ctype="text/html", robots=None):
    def h(req: httpx.Request):
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text=robots) if robots is not None else httpx.Response(404)
        return httpx.Response(200, text=body, headers={"content-type": ctype})
    return h


def test_html_to_text_drops_scripts_and_keeps_blocks():
    t = html_to_text("<html><title>T</title><script>evil()</script><style>x{}</style><h1>Head</h1><p>a  b</p><p>c</p></html>")
    assert t == "Head\na b\nc"


async def test_fetch_ok():
    p = await fetcher(page_handler()).fetch_text("https://uni.edu/page")
    assert p.text == "Hello world"


async def test_fetch_respects_robots():
    with pytest.raises(FetchError, match="robots"):
        await fetcher(page_handler(robots="User-agent: *\nDisallow: /")).fetch_text("https://uni.edu/page")
    with pytest.raises(FetchError, match="robots"):   # unreachable/5xx robots => disallow
        await fetcher(lambda r: httpx.Response(503)).fetch_text("https://uni.edu/page")


@pytest.mark.parametrize("url", ["http://127.0.0.1/admin", "http://169.254.169.254/latest", "http://[::1]/",
                                 "ftp://uni.edu/x", "file:///etc/passwd"])
async def test_fetch_blocks_non_public_and_non_http(url):
    with pytest.raises(FetchError):
        await fetcher(page_handler()).fetch_text(url)


async def test_fetch_blocks_hostname_resolving_to_private_ip():
    async def private(host):
        return ["10.0.0.5"]
    with pytest.raises(FetchError, match="non-public"):
        await fetcher(page_handler(), resolver=private).fetch_text("https://evil.example/page")


async def test_fetch_revalidates_redirects():
    async def resolver(host):
        return ["10.0.0.5"] if host == "internal.example" else [PUBLIC]

    def h(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "http://internal.example/secret"})

    with pytest.raises(FetchError, match="non-public"):
        await fetcher(h, resolver=resolver).fetch_text("https://uni.edu/redir")


async def test_fetch_rejects_non_text_and_errors():
    with pytest.raises(FetchError, match="content type"):
        await fetcher(page_handler(ctype="application/pdf")).fetch_text("https://uni.edu/a.pdf")
    with pytest.raises(FetchError, match="HTTP 404"):
        await fetcher(lambda r: httpx.Response(404)).fetch_text("https://uni.edu/x")
    with pytest.raises(FetchError, match="no readable text"):
        await fetcher(page_handler("<html><script>x</script></html>")).fetch_text("https://uni.edu/js")


def test_official_domain_heuristic():
    assert all(is_probably_official(u) for u in
               ["https://www.mit.edu/x", "https://ox.ac.uk/y", "https://unimelb.edu.au/z", "https://mext.go.jp/a"])
    assert not any(is_probably_official(u) for u in
                   ["https://acme.com/jobs", "https://edu.example.com/x", "https://scholarship-blog.org/p"])


# ---------------------------------------------------------------- enriched /run
PAGE_HTML = ("<html><body><h1>MSc in AI</h1><p>Applicants must have a bachelor's degree in computer science. "
             "Tuition fees are waived and a monthly stipend of €1,200 is paid.</p>"
             "<p>Application deadline: 15 January 2027.</p></body></html>")


@pytest.fixture
def env():
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    sf = make_session_factory(engine)
    with sf() as s:
        r = UserRepository(s)
        r.save_profile(r.get_or_create_by_telegram(1), load_profile(EXAMPLE).model_dump(mode="json"))
        s.commit()
    return sf


def bot_for(sf, url, body=PAGE_HTML, llm=None, **kw):
    t = MockTransport()
    search = MockSearchProvider([SearchResult("MSc in AI at Example University", url, "snippet", "brave")])
    bot = BotHandler(sf, t, providers=[search], llm=llm, fetcher=fetcher(page_handler(body)),
                     max_pages=3, clock=lambda: NOW, **kw)
    return bot, t


async def test_run_enriches_official_page_with_rules(env):
    bot, t = bot_for(env, "https://www.example.edu/msc-ai")
    await bot.handle(1, "/run")
    report = "\n".join(m for _, m in t.sent)
    head = report.split("━━ ۵.")[0]
    assert "MSc in AI at Example University" in head and "واجد شرایط" in head   # eligible, verified
    assert "روش استخراج: rules" in report and "صفحات بررسی‌شده: 1" in report
    with env() as s:
        o = s.scalars(select(Opportunity)).one()
        assert o.verification_status == "verified" and o.official_url == "https://www.example.edu/msc-ai"
        assert o.funding_type == "full" and o.stipend == "€1,200" and o.deadline.date().isoformat() == "2027-01-15"
        assert "rules" in o.verification_notes
        claims = {e.claim for e in s.scalars(select(OpportunityEvidence))}
        assert {"degree_required_at_application", "deadline", "funding_type"} <= claims


async def test_non_official_source_stays_unverified_and_never_hard_rejects(env):
    master_page = "<html><body><p>Applicants must hold a completed master's degree.</p></body></html>"
    bot, t = bot_for(env, "https://scholarship-blog.com/msc", body=master_page)
    await bot.handle(1, "/run")
    report = "\n".join(m for _, m in t.sent)
    head, rest = report.split("━━ ۵.")
    assert "MSc in AI at Example University" not in head                  # not actionable
    assert "اطلاعات رسمی تأییدشده در دسترس نیست" in rest                     # unverified
    assert "مدرک تکمیل‌شده لازم است" not in rest                           # unofficial claim is not a confirmed rejection
    with env() as s:
        assert s.scalars(select(Opportunity)).one().verification_status == "unverified"


async def test_run_uses_llm_and_records_usage(env):
    reply = json.dumps({"degree_required_at_application": "bachelor",
                        "evidence": {"degree_required_at_application": "Applicants must have a bachelor's degree"}})
    llm = MockLLMProvider(reply)
    bot, t = bot_for(env, "https://www.example.edu/msc-ai", llm=llm, cost_fn=lambda i, o: 0.5)
    await bot.handle(1, "/run")
    assert len(llm.calls) == 1
    system, user = llm.calls[0]
    assert "SECRET" not in user and "Bearer" not in user and "research_interests" not in user  # no profile sent
    assert "روش استخراج: llm:mock:mock" in "\n".join(m for _, m in t.sent)
    with env() as s:
        assert s.scalars(select(Opportunity)).one().verification_status == "partially_verified"


async def test_llm_usage_and_cost_are_recorded(env):
    from open_scholar.llm.base import Usage
    llm = MockLLMProvider("{}", Usage(1200, 300))
    bot, _ = bot_for(env, "https://www.example.edu/msc-ai", llm=llm, cost_fn=lambda i, o: (i + o) / 1000)
    await bot.handle(1, "/run")
    with env() as s:
        u = s.scalars(select(ProviderUsage)).one()
        assert (u.provider, u.input_tokens, u.output_tokens, u.est_cost_usd) == ("mock", 1200, 300, 1.5)


async def test_run_falls_back_to_rules_when_llm_breaks(env):
    bot, t = bot_for(env, "https://www.example.edu/msc-ai", llm=MockLLMProvider("garbage"))
    await bot.handle(1, "/run")
    report = "\n".join(m for _, m in t.sent)
    assert "روش استخراج: rules" in report
    with env() as s:
        o = s.scalars(select(Opportunity)).one()
        assert o.verification_status == "verified" and "LLM failed" in o.verification_notes


async def test_failed_fetch_is_reported_not_fatal(env):
    t = MockTransport()
    search = MockSearchProvider([SearchResult("X", "https://www.example.edu/x", "", "brave")])
    bot = BotHandler(env, t, providers=[search], fetcher=fetcher(lambda r: httpx.Response(404)),
                     max_pages=3, clock=lambda: NOW)
    await bot.handle(1, "/run")
    report = "\n".join(m for _, m in t.sent)
    assert "ناموفق: 1" in report and "اطلاعات رسمی تأییدشده در دسترس نیست" in report
    with env() as s:
        assert s.scalars(select(Opportunity)).one().verification_notes.startswith("fetch failed")


async def test_max_pages_bounds_fetching(env):
    t = MockTransport()
    results = [SearchResult(f"P{i}", f"https://www.example.edu/p{i}", "", "brave") for i in range(6)]
    fetched = []

    def h(req):
        if req.url.path != "/robots.txt":
            fetched.append(req.url.path)
        return page_handler()(req)

    bot = BotHandler(env, t, providers=[MockSearchProvider(results)], fetcher=fetcher(h),
                     max_pages=2, clock=lambda: NOW)
    await bot.handle(1, "/run")
    assert len(fetched) == 2
