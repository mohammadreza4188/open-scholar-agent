"""Load a user profile from YAML/JSON, accepting the MISSION.md 'education' layout."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from open_scholar.core.profile import PROFILE_SCHEMA_VERSION, UserProfile

_LEGACY_KEYS = {"bachelor": "bachelor", "current_master": "master", "master": "master",
                "current_phd": "phd", "phd": "phd"}


def _degree_from_legacy(key: str, d: dict[str, Any]) -> dict[str, Any]:
    d = dict(d)
    completed = bool(d.pop("completed", False))
    d.pop("currently_enrolled", None)  # derived from `completed`; avoids contradictory flags
    out = {"level": _LEGACY_KEYS[key],
           "status": "completed" if completed else "in_progress"}
    if "enrollment" in d:
        out["start"] = d.pop("enrollment")
    out.update(d)
    return out


def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert the user-friendly `profile.education` layout to the canonical schema."""
    body = dict(raw.get("profile", raw))
    edu = body.pop("education", None)
    if edu:
        body["degrees"] = [_degree_from_legacy(k, v) for k, v in edu.items() if k in _LEGACY_KEYS]
    body.setdefault("schema_version", raw.get("schema_version", PROFILE_SCHEMA_VERSION))
    return body


def load_profile(path: str | Path) -> UserProfile:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    raw = json.loads(text) if p.suffix == ".json" else yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ValueError(f"{p} must contain a mapping at top level")
    return UserProfile.model_validate(normalize(raw))
