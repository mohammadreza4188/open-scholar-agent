"""Requirement extraction orchestrator: LLM when configured, rules otherwise; always grounded."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

from open_scholar.core.opportunity import FundingType, OpportunityRecord, Requirements, VerificationStatus
from open_scholar.llm.base import LLMError, LLMProvider
from open_scholar.llm.schemas import ExtractedRequirements

from .grounding import ground
from .rules import extract_with_rules

log = logging.getLogger(__name__)

_OFFICIAL_SUFFIXES = (".edu", ".gov", ".mil", ".int")
_OFFICIAL_SLD = ("ac", "edu", "gov", "go")  # e.g. ox.ac.uk, unimelb.edu.au, mext.go.jp


def is_probably_official(url: str) -> bool:
    """HEURISTIC: academic/government domains. Company sites are NOT detected (stay unverified)."""
    host = (urlparse(url).hostname or "").lower()
    parts = host.split(".")
    return host.endswith(_OFFICIAL_SUFFIXES) or (len(parts) >= 3 and parts[-2] in _OFFICIAL_SLD)


@dataclass
class ExtractionOutcome:
    extracted: ExtractedRequirements
    method: str                      # "rules" | "llm:<provider>:<model>"
    notes: list[str] = field(default_factory=list)


async def extract_requirements(text: str, llm: LLMProvider | None) -> ExtractionOutcome:
    notes: list[str] = []
    if llm is not None:
        try:
            raw = await llm.extract_requirements(text)
            grounded, dropped = ground(raw, text)
            return ExtractionOutcome(grounded, f"llm:{llm.name}:{llm.model}", dropped)
        except LLMError as e:
            log.warning("LLM extraction failed (%s); falling back to rules", e)
            notes.append(f"LLM failed ({e}); used rules")
    grounded, dropped = ground(extract_with_rules(text), text)
    return ExtractionOutcome(grounded, "rules", notes + dropped)


def apply_extraction(rec: OpportunityRecord, ext: ExtractedRequirements, url: str) -> OpportunityRecord:
    """Merge grounded facts into the record and assign a verification status."""
    official = is_probably_official(url)
    req = Requirements(
        degree_required_at_application=ext.degree_required_at_application,
        degree_required_before_enrollment=ext.degree_required_before_enrollment,
        active_enrollment_required=ext.active_enrollment_required,
        enrollment_level=ext.enrollment_level,
        excluded_previous_enrollment=ext.excluded_previous_enrollment,
        excluded_completed_degree=ext.excluded_completed_degree,
        allowed_nationalities=ext.allowed_nationalities or None,
        excluded_nationalities=ext.excluded_nationalities or None,
        source_url=url, official=official,
        evidence_quote=ext.evidence.get("degree_required_at_application"))
    deadline = None
    if ext.deadline:
        try:
            deadline = datetime.fromisoformat(ext.deadline)  # date-only, naive
        except ValueError:
            pass
    degree_known = ext.degree_required_at_application is not None
    funding_known = ext.funding_type != FundingType.UNKNOWN
    if official and degree_known and funding_known and deadline:
        status = VerificationStatus.VERIFIED
    elif official and (degree_known or funding_known or deadline):
        status = VerificationStatus.PARTIALLY_VERIFIED
    else:
        status = VerificationStatus.UNVERIFIED
    return rec.model_copy(update={
        "requirements": req,
        "official_url": url if official else rec.official_url,
        "funding_type": ext.funding_type if funding_known else rec.funding_type,
        "tuition_coverage": ext.tuition_coverage or rec.tuition_coverage,
        "stipend": ext.stipend or rec.stipend,
        "deadline": deadline or rec.deadline,
        "deadline_has_time": False if deadline else rec.deadline_has_time,
        "verification_status": status,
    })
