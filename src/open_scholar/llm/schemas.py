"""Pydantic schemas for structured LLM output. All model output is validated against these."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from open_scholar.core.opportunity import FundingType
from open_scholar.core.profile import DegreeLevel


class ExtractedRequirements(BaseModel):
    """Facts a page EXPLICITLY states. None / 'unknown' / [] always means 'not stated'."""
    model_config = ConfigDict(extra="ignore")

    degree_required_at_application: DegreeLevel | None = None
    degree_required_before_enrollment: DegreeLevel | None = None
    active_enrollment_required: bool | None = None
    enrollment_level: DegreeLevel | None = None
    excluded_previous_enrollment: DegreeLevel | None = None
    excluded_completed_degree: DegreeLevel | None = None
    allowed_nationalities: list[str] = Field(default_factory=list)
    excluded_nationalities: list[str] = Field(default_factory=list)
    funding_type: FundingType = FundingType.UNKNOWN
    tuition_coverage: str | None = None
    stipend: str | None = None
    deadline: str | None = None  # ISO date YYYY-MM-DD
    # field name -> verbatim quote copied from the page (checked by verification.grounding)
    evidence: dict[str, str] = Field(default_factory=dict)


class OpportunityAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
