"""Clearly-labelled DEMO opportunities for local development. They are NOT real."""
from __future__ import annotations

from datetime import datetime, timedelta

from open_scholar.core.opportunity import (Category, FundingType, OpportunityRecord, Requirements,
                                           VerificationStatus as V)
from open_scholar.core.profile import DegreeLevel as L


def demo_opportunities(now: datetime) -> list[OpportunityRecord]:
    def req(**kw):
        return Requirements(official=True, source_url="https://example.org/demo", **kw)

    common = dict(organization="Demo University", country="Demo Country",
                  official_url=None, application_url=None, verification_status=V.VERIFIED)
    d = lambda days: (now + timedelta(days=days)).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
    return [
        OpportunityRecord(title="[DEMO] Funded MSc in Machine Learning", category=Category.MASTERS,
                          field="Machine Learning", funding_type=FundingType.FULL, tuition_coverage="full",
                          stipend="demo stipend", deadline=d(3),
                          requirements=req(degree_required_at_application=L.BACHELOR),
                          **{**common, "official_url": "https://example.org/demo/msc-ml"}),
        OpportunityRecord(title="[DEMO] Second MSc (needs completed Master's)", category=Category.MASTERS,
                          field="Artificial Intelligence", funding_type=FundingType.FULL, deadline=d(40),
                          requirements=req(degree_required_at_application=L.MASTER),
                          **{**common, "official_url": "https://example.org/demo/msc-2"}),
        OpportunityRecord(title="[DEMO] Paid AI research internship", category=Category.INTERNSHIP,
                          field="Deep Learning", funding_type=FundingType.PARTIAL, stipend="demo stipend",
                          duration="3 months", deadline=d(20),
                          requirements=req(degree_required_at_application=L.BACHELOR,
                                           active_enrollment_required=True, enrollment_level=L.MASTER),
                          **{**common, "official_url": "https://example.org/demo/intern"}),
        OpportunityRecord(title="[DEMO] Direct-entry PhD in NLP", category=Category.PHD,
                          field="Natural Language Processing", funding_type=FundingType.FULL, deadline=d(60),
                          requirements=req(degree_required_at_application=L.BACHELOR,
                                           degree_required_before_enrollment=L.MASTER),
                          **{**common, "official_url": "https://example.org/demo/phd-b"}),
        OpportunityRecord(title="[DEMO] PhD requiring Master's", category=Category.PHD,
                          field="Machine Learning", funding_type=FundingType.FULL, deadline=d(60),
                          requirements=req(degree_required_at_application=L.MASTER),
                          **{**common, "official_url": "https://example.org/demo/phd-c"}),
    ]
