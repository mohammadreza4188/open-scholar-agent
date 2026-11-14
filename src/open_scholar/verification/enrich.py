"""Fetch discovered pages and extract requirements for opportunities that still lack them."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from open_scholar.database import opportunity_repo as repo
from open_scholar.database.models import Opportunity
from open_scholar.llm.base import LLMProvider

from .extract import apply_extraction, extract_requirements
from .fetch import FetchError, PageFetcher

log = logging.getLogger(__name__)


@dataclass
class EnrichStats:
    fetched: int = 0
    failed: dict[str, str] = field(default_factory=dict)   # url -> reason
    methods: set[str] = field(default_factory=set)


async def enrich_pending(session: Session, fetcher: PageFetcher, llm: LLMProvider | None,
                         limit: int, now: datetime) -> EnrichStats:
    stats = EnrichStats()
    rows = session.scalars(
        select(Opportunity).where(
            Opportunity.canonical_url.is_not(None),
            Opportunity.verification_status == "unverified",
            or_(Opportunity.verification_notes.is_(None), Opportunity.verification_notes.like("fetch failed%")),
        ).order_by(Opportunity.id).limit(limit)).all()
    for row in rows:
        url = row.canonical_url
        try:
            page = await fetcher.fetch_text(url)
        except FetchError as e:
            row.verification_notes = f"fetch failed: {e}"
            stats.failed[url] = str(e)
            continue
        stats.fetched += 1
        outcome = await extract_requirements(page.text, llm)
        stats.methods.add(outcome.method)
        rec = apply_extraction(repo.to_record(row), outcome.extracted, page.url)
        repo.update(session, row, rec, now=now)
        official = rec.requirements.official
        for claim, quote in outcome.extracted.evidence.items():
            repo.add_evidence(session, row, claim, quote, page.url, official)
        row.verification_notes = (f"extracted by {outcome.method}; "
                                  f"{'official-domain heuristic matched' if official else 'source not recognised as official'}"
                                  + (f"; {'; '.join(outcome.notes)}" if outcome.notes else ""))
    return stats
