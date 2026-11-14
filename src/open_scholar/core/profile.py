"""Versioned, validated user profile schema.

Academic status is modeled explicitly so that "enrolled in a Master's" is never
confused with "holds a Master's" (see MISSION.md section 2).
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PROFILE_SCHEMA_VERSION = 1


class DegreeLevel(StrEnum):
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"


DEGREE_ORDER = {DegreeLevel.BACHELOR: 1, DegreeLevel.MASTER: 2, DegreeLevel.PHD: 3}


class DegreeStatus(StrEnum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"


class GPA(BaseModel):
    value: float
    scale: float

    @model_validator(mode="after")
    def _check(self) -> "GPA":
        if self.scale <= 0 or not (0 <= self.value <= self.scale):
            raise ValueError("GPA must satisfy 0 <= value <= scale and scale > 0")
        return self

    @property
    def normalized(self) -> float:
        """GPA as a 0..1 fraction."""
        return self.value / self.scale

    @classmethod
    def parse(cls, text: str) -> "GPA":
        try:
            v, s = text.replace(" ", "").split("/")
            return cls(value=float(v), scale=float(s))
        except ValueError as e:
            raise ValueError(f"GPA must look like '16.47/20', got {text!r}") from e


class DegreeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    level: DegreeLevel
    status: DegreeStatus
    degree: str | None = None
    specialization: str | None = None
    university: str | None = None
    country: str | None = None
    gpa: GPA | None = None
    start: str | None = None  # free-form e.g. "October 2026" until date parsing lands
    expected_graduation: str | None = None

    @field_validator("gpa", mode="before")
    @classmethod
    def _gpa(cls, v):
        return GPA.parse(v) if isinstance(v, str) else v


class Project(BaseModel):
    name: str
    technologies: list[str] = Field(default_factory=list)


class FundingPreferences(BaseModel):
    full_funding: bool = True
    partial_funding: bool = True
    paid_internships: bool = True


class Preferences(BaseModel):
    priority_order: list[str] = Field(
        default_factory=lambda: ["funded_masters", "paid_internships", "direct_entry_phd"])
    worldwide: bool = True
    preferred_countries: list[str] = Field(default_factory=list)
    exclude_countries: list[str] = Field(default_factory=list)
    funding: FundingPreferences = Field(default_factory=FundingPreferences)


class UserProfile(BaseModel):
    """Core profile. Contains no sensitive identifiers by design."""
    model_config = ConfigDict(extra="forbid")
    schema_version: int = PROFILE_SCHEMA_VERSION
    degrees: list[DegreeRecord] = Field(default_factory=list)
    research_interests: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    languages: dict[str, str] = Field(default_factory=dict)  # language -> level / test score
    nationality: str | None = None
    preferences: Preferences = Field(default_factory=Preferences)

    # --- academic status helpers (never conflate in-progress with completed) ---
    def has_completed(self, level: DegreeLevel) -> bool:
        return any(d.level == level and d.status == DegreeStatus.COMPLETED for d in self.degrees)

    def is_enrolled(self, level: DegreeLevel) -> bool:
        return any(d.level == level and d.status == DegreeStatus.IN_PROGRESS for d in self.degrees)

    def has_completed_at_least(self, level: DegreeLevel) -> bool:
        """A completed degree at `level` or above. In-progress degrees never count."""
        return any(d.status == DegreeStatus.COMPLETED and DEGREE_ORDER[d.level] >= DEGREE_ORDER[level]
                   for d in self.degrees)

    def has_any_record(self, level: DegreeLevel) -> bool:
        """Completed OR in-progress degree at exactly `level` (for 'previous enrollment' rules)."""
        return any(d.level == level for d in self.degrees)

    @property
    def highest_completed(self) -> DegreeLevel | None:
        for lvl in (DegreeLevel.PHD, DegreeLevel.MASTER, DegreeLevel.BACHELOR):
            if self.has_completed(lvl):
                return lvl
        return None
