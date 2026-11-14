"""Opportunity persistence: fingerprint-based duplicate detection and change tracking."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from open_scholar.core.opportunity import (Category, FundingType, OpportunityRecord, Requirements,
                                           VerificationStatus)

from .models import Opportunity, OpportunityChange, OpportunityEvidence

_TRACKED = ("deadline", "funding_type", "verification_status", "application_url")
_IGNORE_NEW = {"funding_type": "unknown", "verification_status": "unverified"}  # never downgrade to "unknown"


def normalize_url(url: str) -> str:
    p = urlparse(url.strip())
    host = p.netloc.lower().removeprefix("www.")
    return f"{host}{p.path.rstrip('/')}"


def fingerprint(rec: OpportunityRecord, discovered_url: str | None = None) -> str:
    url = rec.official_url or discovered_url
    key = normalize_url(url) if url else \
        re.sub(r"\s+", " ", f"{rec.organization or ''}|{rec.title}".casefold()).strip()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _utc(dt: datetime | None, has_time: bool) -> datetime | None:
    # SQLite drops tzinfo; store timed deadlines in UTC, date-only deadlines as given.
    if dt is not None and has_time and dt.tzinfo:
        return dt.astimezone(timezone.utc)
    return dt


def upsert(session: Session, rec: OpportunityRecord, discovered_url: str | None = None,
           now: datetime | None = None) -> tuple[Opportunity, bool]:
    """Insert or update. Returns (row, created). Same URL (or org+title) never creates a duplicate."""
    now = now or datetime.now(timezone.utc)
    fp = fingerprint(rec, discovered_url)
    row = session.scalar(select(Opportunity).where(Opportunity.fingerprint == fp))
    created = row is None
    if created:
        row = Opportunity(fingerprint=fp, title=rec.title, first_seen=now)
        session.add(row)
    update(session, row, rec, discovered_url, now, created)
    return row, created


def update(session: Session, row: Opportunity, rec: OpportunityRecord, discovered_url: str | None = None,
           now: datetime | None = None, created: bool = False) -> None:
    """Apply `rec` to `row` without ever erasing known facts with 'unknown'; record tracked changes."""
    now = now or datetime.now(timezone.utc)
    new_vals = {
        "title": rec.title, "organization": rec.organization, "country": rec.country,
        "category": rec.category.value, "field": rec.field, "official_url": rec.official_url,
        "application_url": rec.application_url, "canonical_url": discovered_url or rec.official_url,
        "funding_type": rec.funding_type.value, "tuition_coverage": rec.tuition_coverage or "unknown",
        "stipend": rec.stipend, "duration": rec.duration, "start_date": rec.start_date,
        "deadline": _utc(rec.deadline, rec.deadline_has_time), "deadline_has_time": rec.deadline_has_time,
        "deadline_timezone": rec.deadline_timezone, "verification_status": rec.verification_status.value,
    }
    for k, new in new_vals.items():
        old = getattr(row, k)
        if not created and (new is None or new == _IGNORE_NEW.get(k) or new == "unknown"):
            continue  # a thinner rediscovery must not erase known facts
        if not created and k in _TRACKED and old != new:
            session.add(OpportunityChange(opportunity=row, field=k, old_value=str(old), new_value=str(new)))
        setattr(row, k, new)
    if created or rec.requirements != Requirements():
        row.requirements = rec.requirements.model_dump(mode="json")
    row.last_checked = now
    session.flush()


def add_evidence(session: Session, row: Opportunity, claim: str, quote: str, source_url: str,
                 official: bool) -> None:
    exists = any(e.claim == claim and e.quote == quote for e in row.evidence)
    if not exists:
        session.add(OpportunityEvidence(opportunity=row, claim=claim, quote=quote[:2000],
                                        source_url=source_url, is_official=official))


def to_record(row: Opportunity) -> OpportunityRecord:
    dl = row.deadline
    if dl is not None and row.deadline_has_time and dl.tzinfo is None:
        dl = dl.replace(tzinfo=timezone.utc)
    return OpportunityRecord(
        title=row.title, organization=row.organization, country=row.country,
        category=Category(row.category), field=row.field, official_url=row.official_url,
        application_url=row.application_url, funding_type=FundingType(row.funding_type),
        tuition_coverage=None if row.tuition_coverage == "unknown" else row.tuition_coverage,
        stipend=row.stipend, duration=row.duration, start_date=row.start_date, deadline=dl,
        deadline_has_time=row.deadline_has_time, deadline_timezone=row.deadline_timezone,
        verification_status=VerificationStatus(row.verification_status),
        requirements=Requirements.model_validate(row.requirements or {}))


def list_all(session: Session) -> list[Opportunity]:
    return list(session.scalars(select(Opportunity).order_by(Opportunity.id)))
