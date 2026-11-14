"""Deterministic, LLM-independent eligibility engine (MISSION.md section 7).

Eligibility status and profile match score are SEPARATE outputs. The score never
influences the status: a hard failed requirement always yields NOT_ELIGIBLE.
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from open_scholar.core.opportunity import OpportunityRecord, VerificationStatus
from open_scholar.core.profile import DegreeLevel, DegreeStatus, UserProfile


class EligibilityStatus(StrEnum):
    ELIGIBLE = "eligible"
    LIKELY_ELIGIBLE = "likely_eligible"
    UNCERTAIN = "uncertain"
    NOT_ELIGIBLE = "not_eligible"


class CheckResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"          # requirement or profile fact missing
    CONDITIONAL = "conditional"  # satisfiable later (e.g. degree in progress)


class Check(BaseModel):
    code: str
    requirement: str
    profile_fact: str
    result: CheckResult
    explanation: str
    confidence: str = "low"  # "high" only when the requirement comes from an official source
    source_url: str | None = None


class EligibilityDecision(BaseModel):
    status: EligibilityStatus
    checks: list[Check] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    match_score: float | None = None  # filled by ranking; never used to decide status

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if c.result == CheckResult.FAIL]


def _degree_fact(profile: UserProfile, level: DegreeLevel) -> str:
    done = profile.has_completed(level)
    prog = profile.is_enrolled(level)
    if done:
        return f"{level.value}: completed"
    if prog:
        return f"{level.value}: in progress (NOT completed)"
    return f"{level.value}: none"


def _best_gpa(profile: UserProfile) -> float | None:
    vals = [d.gpa.normalized for d in profile.degrees if d.gpa]
    return max(vals) if vals else None


def evaluate_eligibility(opp: OpportunityRecord, profile: UserProfile) -> EligibilityDecision:
    r = opp.requirements
    conf = "high" if r.official else "low"
    src = r.source_url
    checks: list[Check] = []

    def add(code, requirement, fact, result, explanation):
        checks.append(Check(code=code, requirement=requirement, profile_fact=fact, result=result,
                            explanation=explanation, confidence=conf, source_url=src))

    # 0. Opportunity state
    if opp.verification_status in (VerificationStatus.CLOSED, VerificationStatus.WITHDRAWN):
        add("opportunity_open", "Opportunity must be open", f"status: {opp.verification_status.value}",
            CheckResult.FAIL, f"Opportunity is {opp.verification_status.value}.")

    # 1. Degree completed at application time
    req = r.degree_required_at_application
    if req is None:
        add("degree_at_application", "Degree required at application: unknown", "-", CheckResult.UNKNOWN,
            "Official degree requirement could not be determined.")
    else:
        ok = profile.has_completed_at_least(req)
        add("degree_at_application", f"Completed {req.value} degree at application time",
            _degree_fact(profile, req), CheckResult.PASS if ok else CheckResult.FAIL,
            f"A completed {req.value} degree is {'held' if ok else 'required but not held'}"
            + ("" if ok or not profile.is_enrolled(req) else "; a degree in progress does not count."))

    # 2. Degree required before enrollment (may be satisfied later)
    # TODO(Phase 3): graduation/start dates are free text today, so an in-progress degree is always
    # CONDITIONAL (-> Likely Eligible). Parse dates strictly and compare expected graduation with the
    # program start; return FAIL when graduation is provably after enrollment.
    pre = r.degree_required_before_enrollment
    if pre is not None:
        if profile.has_completed_at_least(pre):
            res, why = CheckResult.PASS, "Already completed."
        elif profile.is_enrolled(pre):
            res, why = (CheckResult.CONDITIONAL,
                        "Degree is in progress; must be completed before enrollment (graduation date unconfirmed).")
        else:
            res, why = CheckResult.UNKNOWN, "No completed or in-progress degree at this level; cannot confirm."
        add("degree_before_enrollment", f"Completed {pre.value} degree before enrollment",
            _degree_fact(profile, pre), res, why)

    # 3. Active enrollment
    if r.active_enrollment_required:
        lvl = r.enrollment_level
        enrolled = profile.is_enrolled(lvl) if lvl else any(
            d.status == DegreeStatus.IN_PROGRESS for d in profile.degrees)
        add("active_enrollment", f"Active enrollment required{f' ({lvl.value})' if lvl else ''}",
            "currently enrolled" if enrolled else "not currently enrolled",
            CheckResult.PASS if enrolled else CheckResult.FAIL,
            "Active enrollment satisfied." if enrolled else "Active enrollment is required but not satisfied.")

    # 4. Previous enrollment prohibited
    if r.excluded_previous_enrollment:
        lvl = r.excluded_previous_enrollment
        has = profile.has_any_record(lvl)
        add("previous_enrollment", f"No previous or current {lvl.value} enrollment allowed",
            _degree_fact(profile, lvl), CheckResult.FAIL if has else CheckResult.PASS,
            f"Applicant has prior/current {lvl.value} enrollment, which is excluded." if has
            else f"No {lvl.value} enrollment on record.")

    # 5. Holders of a completed degree excluded
    if r.excluded_completed_degree:
        lvl = r.excluded_completed_degree
        has = profile.has_completed_at_least(lvl)
        add("completed_degree_excluded", f"Applicants with completed {lvl.value} excluded",
            _degree_fact(profile, lvl), CheckResult.FAIL if has else CheckResult.PASS,
            "Applicant already holds the excluded degree." if has else "Applicant does not hold the excluded degree.")

    # 6. Nationality
    if r.allowed_nationalities is not None or r.excluded_nationalities is not None:
        nat = profile.nationality
        if nat is None:
            add("nationality", "Nationality restriction applies", "nationality not in profile",
                CheckResult.UNKNOWN, "Add nationality to the profile to evaluate this restriction.")
        else:
            n = nat.casefold()
            allowed = r.allowed_nationalities
            blocked = (allowed is not None and n not in {a.casefold() for a in allowed}) or \
                      (r.excluded_nationalities is not None and n in {a.casefold() for a in r.excluded_nationalities})
            add("nationality", "Nationality restriction", f"nationality: {nat}",
                CheckResult.FAIL if blocked else CheckResult.PASS,
                "Nationality is excluded." if blocked else "Nationality is permitted.")

    # 7. Minimum GPA
    if r.min_gpa_fraction is not None:
        g = _best_gpa(profile)
        if g is None:
            add("gpa", f"GPA >= {r.min_gpa_fraction:.0%} of scale", "no GPA in profile", CheckResult.UNKNOWN,
                "GPA missing from profile.")
        else:
            ok = g >= r.min_gpa_fraction
            add("gpa", f"GPA >= {r.min_gpa_fraction:.0%} of scale", f"GPA {g:.0%} of scale",
                CheckResult.PASS if ok else CheckResult.FAIL, "GPA meets minimum." if ok else "GPA below minimum.")

    return EligibilityDecision(status=_aggregate(checks, opp), checks=checks,
                               unresolved=[c.explanation for c in checks
                                           if c.result in (CheckResult.UNKNOWN, CheckResult.CONDITIONAL)])


def _aggregate(checks: list[Check], opp: OpportunityRecord) -> EligibilityStatus:
    results = {c.result for c in checks}
    if CheckResult.FAIL in results:
        return EligibilityStatus.NOT_ELIGIBLE  # hard failure; nothing can override it
    if CheckResult.UNKNOWN in results or opp.verification_status == VerificationStatus.UNVERIFIED:
        return EligibilityStatus.UNCERTAIN     # never guess; unverified is never "confirmed"
    if CheckResult.CONDITIONAL in results or opp.verification_status == VerificationStatus.PARTIALLY_VERIFIED:
        return EligibilityStatus.LIKELY_ELIGIBLE
    return EligibilityStatus.ELIGIBLE
