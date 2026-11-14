"""Per-user run: search -> store -> evaluate (DB opportunities) -> Persian report."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from open_scholar.core.opportunity import Category, OpportunityRecord
from open_scholar.core.profile import UserProfile
from open_scholar.database import opportunity_repo as repo
from open_scholar.database.models import EligibilityResult, SearchRun, User
from open_scholar.eligibility.engine import EligibilityDecision, evaluate_eligibility
from open_scholar.notifications.report import ReportEntry, SearchSummary, build_daily_report
from open_scholar.ranking.score import match_score
from open_scholar.search.base import SearchProvider
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
                       now: datetime | None = None) -> str:
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

    evaluated = evaluate_all(session, user, profile, now)
    run.sources_checked, run.sources_failed = checked, [f"{k}: {v}" for k, v in failed.items()]
    run.new_count, run.finished_at, run.status = new_count, now, "ok" if checked else "failed"
    session.flush()

    return build_daily_report([ReportEntry(rec, dec) for _, rec, dec in evaluated],
                              SearchSummary(checked, failed, new_count), now, user.timezone)
