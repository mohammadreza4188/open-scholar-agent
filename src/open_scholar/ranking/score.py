"""Configurable 0-100 profile match score. Independent of eligibility status."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from open_scholar.core.opportunity import Category, FundingType, OpportunityRecord
from open_scholar.core.profile import UserProfile


@dataclass
class ScoreWeights:
    field_relevance: float = 50
    funding: float = 20
    gpa: float = 15
    priority: float = 10
    time_left: float = 5


@dataclass
class ScoreResult:
    score: float
    reasons: list[str] = field(default_factory=list)


_PRIORITY_KEY = {Category.MASTERS: "funded_masters", Category.INTERNSHIP: "paid_internships",
                 Category.PHD: "direct_entry_phd"}


def match_score(opp: OpportunityRecord, profile: UserProfile, now: datetime,
                w: ScoreWeights | None = None) -> ScoreResult:
    w = w or ScoreWeights()
    pts, why = 0.0, []

    text = f"{opp.title} {opp.field or ''}".casefold()
    interests = profile.research_interests
    hits = [i for i in interests if i.casefold() in text]
    if interests:
        frac = min(1.0, len(hits) / 2)  # two matched interests = full relevance
        pts += w.field_relevance * frac
        why.append(f"research interests matched: {', '.join(hits) or 'none'}")

    pref = profile.preferences.funding
    ok = (opp.funding_type == FundingType.FULL and pref.full_funding) or \
         (opp.funding_type == FundingType.PARTIAL and pref.partial_funding)
    if ok:
        pts += w.funding
        why.append(f"funding ({opp.funding_type.value}) fits preferences")
    elif opp.funding_type == FundingType.UNKNOWN:
        why.append("funding unknown (no points)")

    gpas = [d.gpa.normalized for d in profile.degrees if d.gpa]
    if gpas:
        pts += w.gpa * max(gpas)
        why.append(f"GPA {max(gpas):.0%} of scale")

    order = profile.preferences.priority_order
    key = _PRIORITY_KEY[opp.category]
    if key in order:
        pts += w.priority * (1 - order.index(key) / max(len(order), 1))
        why.append(f"category priority #{order.index(key) + 1}")

    if opp.deadline:
        dl = opp.deadline if opp.deadline.tzinfo else opp.deadline.replace(tzinfo=now.tzinfo)  # date-only
        days = (dl - now).total_seconds() / 86400
        if days >= 14:
            pts += w.time_left
        elif days >= 0:
            pts += w.time_left * days / 14
        why.append(f"{days:.0f} days until deadline")

    return ScoreResult(round(min(pts, 100.0), 1), why)
