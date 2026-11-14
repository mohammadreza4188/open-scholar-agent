from pathlib import Path

import pytest
from pydantic import ValidationError

from open_scholar.config.profile_loader import load_profile
from open_scholar.core.profile import DegreeLevel, UserProfile

EXAMPLE = Path(__file__).parent.parent / "config" / "profile.example.yaml"


def test_example_profile_distinguishes_enrolled_from_completed():
    p = load_profile(EXAMPLE)
    assert p.has_completed(DegreeLevel.BACHELOR)
    assert p.is_enrolled(DegreeLevel.MASTER)
    assert not p.has_completed(DegreeLevel.MASTER)  # critical rule
    assert p.highest_completed == DegreeLevel.BACHELOR
    assert p.degrees[0].gpa.normalized == pytest.approx(16.47 / 20)
    assert "Fuzzy Systems" in p.research_interests


def test_invalid_gpa_rejected():
    with pytest.raises(ValidationError):
        UserProfile.model_validate({"degrees": [{"level": "bachelor", "status": "completed", "gpa": "25/20"}]})


def test_unknown_fields_rejected():
    with pytest.raises(ValidationError):
        UserProfile.model_validate({"passport_number": "X"})
