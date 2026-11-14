"""Evidence grounding: a claim survives only if its quote appears verbatim in the page.

This is the main defence against hallucinated or injected facts: whatever the extractor
(LLM or rules) returns, ungrounded claims are reset to 'unknown'.
"""
from __future__ import annotations

import re

from open_scholar.llm.schemas import ExtractedRequirements

GROUNDED_FIELDS = [
    "degree_required_at_application", "degree_required_before_enrollment", "active_enrollment_required",
    "excluded_previous_enrollment", "excluded_completed_degree", "allowed_nationalities",
    "excluded_nationalities", "funding_type", "tuition_coverage", "stipend", "deadline",
]
# a quote supporting a degree claim must at least mention that level
_LEVEL_WORDS = {
    "bachelor": ("bachelor", "bsc", "b.sc", "undergraduate"),
    "master": ("master", "msc", "m.sc", "graduate degree"),
    "phd": ("phd", "ph.d", "doctor"),
}
_DEGREE_FIELDS = {"degree_required_at_application", "degree_required_before_enrollment",
                  "excluded_previous_enrollment", "excluded_completed_degree"}
MIN_QUOTE = 8


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("’", "'")).strip().casefold()


def ground(ext: ExtractedRequirements, page_text: str) -> tuple[ExtractedRequirements, list[str]]:
    """Return (grounded copy, notes about dropped claims)."""
    page = norm(page_text)
    out = ExtractedRequirements()
    notes: list[str] = []
    for f in GROUNDED_FIELDS:
        val = getattr(ext, f)
        if val in (None, [], "unknown") or getattr(val, "value", None) == "unknown":
            continue
        quote = ext.evidence.get(f, "")
        ok = len(quote.strip()) >= MIN_QUOTE and norm(quote) in page
        if ok and f in _DEGREE_FIELDS:
            ok = any(w in norm(quote) for w in _LEVEL_WORDS.get(getattr(val, "value", ""), ()))
        if ok:
            setattr(out, f, val)
            out.evidence[f] = quote.strip()
        else:
            notes.append(f"{f}: dropped (no verbatim supporting quote in page)")
    # enrollment_level only makes sense together with a grounded active-enrollment claim
    if out.active_enrollment_required and ext.enrollment_level:
        out.enrollment_level = ext.enrollment_level
    return out, notes
