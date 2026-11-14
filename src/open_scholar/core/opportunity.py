"""Structured opportunity record. None always means 'unknown' - never a guess."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from .profile import DegreeLevel


class Category(StrEnum):
    MASTERS = "masters"
    INTERNSHIP = "internship"
    PHD = "phd"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNVERIFIED = "unverified"
    CLOSED = "closed"
    WITHDRAWN = "withdrawn"


class FundingType(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"
    UNKNOWN = "unknown"


class Requirements(BaseModel):
    """Explicit requirements extracted from an (ideally official) source.

    degree_required_at_application: completed degree needed when applying (None = unknown).
    degree_required_before_enrollment: completed degree needed before the program starts.
    active_enrollment_required: must be currently enrolled (at `enrollment_level`, or any level).
    excluded_previous_enrollment: applicants with ANY prior/current record at this level are barred.
    excluded_completed_degree: applicants who already completed this level (or higher) are barred.
    """
    degree_required_at_application: DegreeLevel | None = None
    degree_required_before_enrollment: DegreeLevel | None = None
    active_enrollment_required: bool | None = None
    enrollment_level: DegreeLevel | None = None
    excluded_previous_enrollment: DegreeLevel | None = None
    excluded_completed_degree: DegreeLevel | None = None
    allowed_nationalities: list[str] | None = None
    excluded_nationalities: list[str] | None = None
    min_gpa_fraction: float | None = None  # 0..1
    source_url: str | None = None
    official: bool = False
    evidence_quote: str | None = None


class OpportunityRecord(BaseModel):
    title: str
    organization: str | None = None
    country: str | None = None
    category: Category
    field: str | None = None
    official_url: str | None = None
    application_url: str | None = None
    funding_type: FundingType = FundingType.UNKNOWN
    tuition_coverage: str | None = None
    stipend: str | None = None
    duration: str | None = None
    start_date: str | None = None
    deadline: datetime | None = None          # timezone-aware if known
    deadline_has_time: bool = False           # False -> date only, exact closing time unconfirmed
    deadline_timezone: str | None = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    requirements: Requirements = Field(default_factory=Requirements)

    @property
    def phd_entry_category(self) -> str | None:
        """A: bachelor suffices; B: master needed before enrollment; C: master needed at application."""
        if self.category != Category.PHD:
            return None
        r = self.requirements
        if r.degree_required_at_application is None:
            return None  # unknown - do not guess
        if r.degree_required_at_application in (DegreeLevel.MASTER, DegreeLevel.PHD):
            return "C"
        return "B" if r.degree_required_before_enrollment in (DegreeLevel.MASTER, DegreeLevel.PHD) else "A"
