"""Conservative regex/rule extractor - the no-LLM fallback.

It only reports what a sentence says plainly and stays silent (None/unknown) on anything
ambiguous. Every claim carries the sentence it came from, so grounding always holds.
"""
from __future__ import annotations

import re
from datetime import datetime

from open_scholar.core.opportunity import FundingType
from open_scholar.core.profile import DegreeLevel
from open_scholar.llm.schemas import ExtractedRequirements

_MASTER = r"(?:master'?s?|m\.?sc\.?)"
_BACH = r"(?:bachelor'?s?|b\.?sc\.?)"
_AMBIGUOUS = re.compile(r"and\s*/\s*or|or equivalent|or higher|bachelor'?s?\s+or\s+master|master'?s?\s+or\s+bachelor", re.I)

_MASTER_REQ = re.compile(
    rf"(?:must\s+(?:have|hold|possess)|requires?|required|completed|holders? of|hold(?:ing)?)[^.]{{0,40}}?\b{_MASTER}\s+(?:degree|diploma)",
    re.I)
_MASTER_BEFORE = re.compile(
    rf"(?:{_MASTER}\s+(?:degree\s+)?(?:must|has to|needs to)\s+be\s+(?:completed|obtained|awarded)\s+before|"
    rf"before\s+(?:the\s+)?(?:start|enrol\w*|commenc\w*)[^.]{{0,40}}{_MASTER})", re.I)
_BACH_REQ = re.compile(
    rf"(?:must\s+(?:have|hold|possess)|requires?|required|holders? of|hold(?:ing)?)[^.]{{0,30}}?\b{_BACH}\s+degree|"
    rf"\b{_BACH}\s+degree\s+(?:is\s+)?(?:required|sufficient)", re.I)
_ENROLLED = re.compile(r"(?:must|have to|need to)\s+be\s+(?:currently\s+)?(?:enrolled|registered)\s+(?:in|as)[^.]{0,60}", re.I)
_NOT_ENROLLED_MASTER = re.compile(rf"(?:not|never)\s+(?:be\s+)?(?:currently\s+)?(?:enrolled|registered)[^.]{{0,40}}{_MASTER}", re.I)
_TUITION = re.compile(r"(?:full\s+tuition\s+(?:waiver|coverage|fee\s+waiver)|tuition\s+(?:fees?\s+)?(?:are\s+)?(?:fully\s+)?(?:waived|covered))", re.I)
_STIPEND = re.compile(
    r"(?:stipend|salary|monthly\s+allowance|living\s+allowance)[^.\n]{0,50}?"
    r"((?:€|\$|£|EUR|USD|GBP)\s?[\d][\d,\.]*|[\d][\d,\.]*\s?(?:€|EUR|USD|GBP|\$))", re.I)
_DEADLINE = re.compile(r"deadline[^.\n:]{0,30}?(?:[:\-–]|\bis\b|\bis on\b)\s*([A-Za-z0-9 ,\-/.]{6,30})", re.I)
_DATE_FORMATS = ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%B %d %Y", "%d %b %Y", "%b %d, %Y", "%d.%m.%Y", "%d/%m/%Y")


def _sentence_around(text: str, m: re.Match) -> str:
    start = max(text.rfind(".", 0, m.start()), text.rfind("\n", 0, m.start())) + 1
    ends = [i for i in (text.find(".", m.end()), text.find("\n", m.end())) if i != -1]
    end = min(ends) + 1 if ends else len(text)
    return re.sub(r"\s+", " ", text[start:end]).strip()[:300]


def _parse_date(s: str) -> str | None:
    s = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", s.strip().rstrip(".,"))
    for n in range(len(s), 5, -1):  # try progressively shorter prefixes ("15 January 2027 at 23:59")
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(s[:n].strip().rstrip(".,"), fmt).date().isoformat()
            except ValueError:
                continue
    return None


def extract_with_rules(text: str) -> ExtractedRequirements:
    out = ExtractedRequirements()
    ev = out.evidence

    def claim(field: str, value, m: re.Match):
        setattr(out, field, value)
        ev[field] = _sentence_around(text, m)

    m = _MASTER_REQ.search(text)
    if m and not _AMBIGUOUS.search(_sentence_around(text, m)):
        claim("degree_required_at_application", DegreeLevel.MASTER, m)
    else:
        m = _BACH_REQ.search(text)
        if m and not _AMBIGUOUS.search(_sentence_around(text, m)):
            claim("degree_required_at_application", DegreeLevel.BACHELOR, m)

    m = _MASTER_BEFORE.search(text)
    if m:
        claim("degree_required_before_enrollment", DegreeLevel.MASTER, m)

    m = _ENROLLED.search(text)
    if m:
        claim("active_enrollment_required", True, m)

    m = _NOT_ENROLLED_MASTER.search(text)
    if m:
        claim("excluded_previous_enrollment", DegreeLevel.MASTER, m)

    t, s = _TUITION.search(text), _STIPEND.search(text)
    if s:
        claim("stipend", s.group(1).strip().rstrip(".,"), s)
    if t:
        claim("tuition_coverage", "full" if re.search(r"full", t.group(0), re.I) else "covered", t)
    # "Fully funded" wording alone is never trusted: full = tuition coverage AND a stated stipend.
    if t and s:
        claim("funding_type", FundingType.FULL, t)
    elif t or s:
        claim("funding_type", FundingType.PARTIAL, t or s)

    m = _DEADLINE.search(text)
    if m and (iso := _parse_date(m.group(1))):
        claim("deadline", iso, m)
    return out
