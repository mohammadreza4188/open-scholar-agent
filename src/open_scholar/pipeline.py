"""Per-user run: search -> store -> evaluate (DB opportunities) -> Persian report."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from open_scholar.core.opportunity import Category, OpportunityRecord
from open_scholar.core.profile import UserProfile
from open_scholar.database import opportunity_repo as repo
from open_scholar.database.models import EligibilityResult, ProviderUsage, SearchRun, User
from open_scholar.eligibility.engine import EligibilityDecision, evaluate_eligibility
from open_scholar.notifications.report import ReportEntry, SearchSummary, build_daily_report
from open_scholar.ranking.score import match_score
from open_scholar.llm.base import LLMProvider
from open_scholar.search.base import SearchProvider
from open_scholar.verification.enrich import EnrichStats, enrich_pending
from open_scholar.verification.fetch import PageFetcher
from open_scholar.search.registry import search_all

# priority key -> (category, query template)
QUERIES = {
    "funded_masters": (Category.MASTERS, "fully funded master's scholarship"),
    "paid_internships": (Category.INTERNSHIP, "paid research internship"),
    "direct_entry_phd": (Category.PHD, "PhD direct entry bachelor's degree"),
}


class NoProfileError(Exception):
    pass


def load_profile(user: User) -> UserProfile:
    if user.profile is None:
        raise NoProfileError("no profile")
    return UserProfile.model_validate(user.profile.data)


def evaluate_all(session: Session, user: User, profile: UserProfile,
                 now: datetime) -> list[tuple[repo.Opportunity, OpportunityRecord, EligibilityDecision]]:
    """Evaluate every stored opportunity for this user only and persist the results."""
    out = []
    excluded = {c.casefold() for c in profile.preferences.exclude_countries}
    for row in repo.list_all(session):
        if row.country and row.country.casefold() in excluded:
            continue
        rec = repo.to_record(row)
        decision = evaluate_eligibility(rec, profile)
        decision.match_score = match_score(rec, profile, now).score
        res = session.scalar(select(EligibilityResult).where(
            EligibilityResult.user_id == user.id, EligibilityResult.opportunity_id == row.id))
        if res is None:
            res = EligibilityResult(user_id=user.id, opportunity_id=row.id)
            session.add(res)
        res.status, res.match_score = decision.status.value, decision.match_score
        res.reasons, res.evaluated_at = [c.model_dump(mode="json") for c in decision.checks], now
        out.append((row, rec, decision))
    return out


async def run_for_user(session: Session, user: User, providers: list[SearchProvider],
                       now: datetime | None = None, *, llm: LLMProvider | None = None,
                       fetcher: PageFetcher | None = None, max_pages: int = 5,
                       cost_fn=lambda i, o: 0.0) -> str:
    now = now or datetime.now(timezone.utc)
    profile = load_profile(user)
    run = SearchRun(user_id=user.id, started_at=now)
    session.add(run)

    checked: list[str] = []
    failed: dict[str, str] = {}
    new_count = 0
    for key in profile.preferences.priority_order:
        if key not in QUERIES:
            continue
        category, template = QUERIES[key]
        query = f"{template} {' '.join(profile.research_interests[:3])}".strip()
        results, ok, bad = await search_all(providers, query)
        checked += [n for n in ok if n not in checked]
        failed.update(bad)
        for r in results:
            # Search snippets are discovery hints only: stored UNVERIFIED with no requirements.
            stub = OpportunityRecord(title=r.title, category=category)
            _, created = repo.upsert(session, stub, discovered_url=r.url, now=now)
            new_count += created

    # Optional enrichment: fetch discovered pages and extract requirements (LLM if configured, else rules).
    stats = EnrichStats()
    if fetcher is not None and max_pages > 0:
        before = llm.totals() if llm else None
        stats = await enrich_pending(session, fetcher, llm, max_pages, now)
        if llm and before is not None:
            after = llm.totals()
            used_in = after.input_tokens - before.input_tokens
            used_out = after.output_tokens - before.output_tokens
            if used_in or used_out:
                session.add(ProviderUsage(user_id=user.id, provider=llm.name, model=llm.model,
                                          input_tokens=used_in, output_tokens=used_out,
                                          est_cost_usd=cost_fn(used_in, used_out), created_at=now))

    evaluated = evaluate_all(session, user, profile, now)
    run.sources_checked, run.sources_failed = checked, [f"{k}: {v}" for k, v in failed.items()]
    run.new_count, run.finished_at, run.status = new_count, now, "ok" if checked else "failed"
    session.flush()

    return build_daily_report([ReportEntry(rec, dec) for _, rec, dec in evaluated],
                              SearchSummary(checked, failed, new_count, stats.fetched, stats.failed,
                                            sorted(stats.methods)), now, user.timezone)
