"""Scenarios A-H from MISSION.md section 17. Users: A, B, C. Opportunities: D-H."""
from datetime import datetime, timezone

import pytest

from open_scholar.core.opportunity import (Category, FundingType, OpportunityRecord, Requirements,
                                           VerificationStatus)
from open_scholar.core.profile import DegreeLevel, UserProfile
from open_scholar.eligibility.engine import CheckResult, EligibilityStatus as S, evaluate_eligibility
from open_scholar.ranking.score import match_score

NOW = datetime(2026, 11, 14, 8, 0, tzinfo=timezone.utc)
B, M, P = DegreeLevel.BACHELOR, DegreeLevel.MASTER, DegreeLevel.PHD


def _profile(*degrees):
    return UserProfile.model_validate({"degrees": list(degrees), "research_interests": ["Machine Learning"]})


BACH = {"level": "bachelor", "status": "completed", "gpa": "16.47/20"}
USERS = {
    "A": _profile(BACH),                                                         # bachelor only
    "B": _profile(BACH, {"level": "master", "status": "in_progress"}),           # enrolled, not completed
    "C": _profile(BACH, {"level": "master", "status": "completed"}),             # master completed
}


def opp(verification=VerificationStatus.VERIFIED, **req) -> OpportunityRecord:
    return OpportunityRecord(title="Test", category=Category.MASTERS, funding_type=FundingType.FULL,
                             verification_status=verification,
                             requirements=Requirements(official=True, source_url="https://uni.example/req", **req))


OPPS = {
    "D": opp(degree_required_at_application=B),                                   # bachelor only
    "E": opp(degree_required_at_application=M),                                   # completed master required
    "F": opp(degree_required_at_application=B, active_enrollment_required=True),  # active enrollment
    "G": opp(degree_required_at_application=B, degree_required_before_enrollment=M),
    "H": opp(degree_required_at_application=B, excluded_previous_enrollment=M),
}

EXPECTED = {
    # (user, opp): status
    ("A", "D"): S.ELIGIBLE, ("B", "D"): S.ELIGIBLE, ("C", "D"): S.ELIGIBLE,
    ("A", "E"): S.NOT_ELIGIBLE, ("B", "E"): S.NOT_ELIGIBLE, ("C", "E"): S.ELIGIBLE,
    ("A", "F"): S.NOT_ELIGIBLE, ("B", "F"): S.ELIGIBLE, ("C", "F"): S.NOT_ELIGIBLE,
    ("A", "G"): S.UNCERTAIN, ("B", "G"): S.LIKELY_ELIGIBLE, ("C", "G"): S.ELIGIBLE,
    ("A", "H"): S.ELIGIBLE, ("B", "H"): S.NOT_ELIGIBLE, ("C", "H"): S.NOT_ELIGIBLE,
}


@pytest.mark.parametrize("pair,expected", EXPECTED.items(), ids=lambda x: "".join(x) if isinstance(x, tuple) else None)
def test_scenario_matrix(pair, expected):
    u, o = pair
    assert evaluate_eligibility(OPPS[o], USERS[u]).status == expected


def test_B_enrolled_master_is_not_completed_master():
    d = evaluate_eligibility(OPPS["E"], USERS["B"])
    assert d.status == S.NOT_ELIGIBLE
    chk = d.failed[0]
    assert "in progress" in chk.profile_fact and "does not count" in chk.explanation
    assert chk.confidence == "high" and chk.source_url == "https://uni.example/req"


def test_G_conditional_is_flagged_with_unresolved_question():
    d = evaluate_eligibility(OPPS["G"], USERS["B"])
    assert any(c.result == CheckResult.CONDITIONAL for c in d.checks) and d.unresolved


def test_high_match_score_never_overrides_hard_ineligibility():
    o = opp(degree_required_at_application=M)
    o.title, o.field = "Machine Learning MSc", "Machine Learning"
    o.deadline = datetime(2027, 3, 1, tzinfo=timezone.utc)
    score = match_score(o, USERS["B"], NOW)
    decision = evaluate_eligibility(o, USERS["B"])
    decision.match_score = score.score
    assert score.score >= 50 and decision.status == S.NOT_ELIGIBLE


def test_unknown_requirement_is_uncertain_not_guessed():
    assert evaluate_eligibility(opp(), USERS["C"]).status == S.UNCERTAIN


def test_unverified_and_partially_verified_are_capped():
    assert evaluate_eligibility(opp(VerificationStatus.UNVERIFIED, degree_required_at_application=B),
                                USERS["A"]).status == S.UNCERTAIN
    assert evaluate_eligibility(opp(VerificationStatus.PARTIALLY_VERIFIED, degree_required_at_application=B),
                                USERS["A"]).status == S.LIKELY_ELIGIBLE


def test_closed_opportunity_not_eligible():
    assert evaluate_eligibility(opp(VerificationStatus.CLOSED, degree_required_at_application=B),
                                USERS["A"]).status == S.NOT_ELIGIBLE


def test_nationality_unknown_vs_excluded():
    o = opp(degree_required_at_application=B, allowed_nationalities=["Germany"])
    assert evaluate_eligibility(o, USERS["A"]).status == S.UNCERTAIN  # nationality missing
    p = USERS["A"].model_copy(update={"nationality": "Iran"})
    assert evaluate_eligibility(o, p).status == S.NOT_ELIGIBLE
