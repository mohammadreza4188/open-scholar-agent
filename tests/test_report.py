from datetime import datetime, timezone

from open_scholar.core.opportunity import (Category, FundingType, OpportunityRecord, Requirements,
                                           VerificationStatus as V)
from open_scholar.core.profile import DegreeLevel as L, UserProfile
from open_scholar.eligibility.engine import evaluate_eligibility
from open_scholar.notifications.report import ReportEntry, SearchSummary, build_daily_report

NOW = datetime(2026, 11, 14, 8, 0, tzinfo=timezone.utc)
USER = UserProfile.model_validate({"degrees": [
    {"level": "bachelor", "status": "completed"}, {"level": "master", "status": "in_progress"}]})


def entry(title, category=Category.MASTERS, funding=FundingType.FULL, ver=V.VERIFIED,
          deadline=None, has_time=False, **req):
    o = OpportunityRecord(title=title, category=category, funding_type=funding, verification_status=ver,
                          deadline=deadline, deadline_has_time=has_time,
                          official_url="https://uni.example",
                          requirements=Requirements(official=True, **req))
    return ReportEntry(o, evaluate_eligibility(o, USER))


def report(entries, summary=None):
    return build_daily_report(entries, summary or SearchSummary(["mock"]), NOW, "Asia/Tehran")


def test_empty_report_says_nothing_found_and_admits_limited_coverage():
    r = report([])
    assert "No new opportunities meeting your eligibility" in r and "کامل یا جهانی نیست" in r


def test_sections_and_rejections():
    es = [
        entry("GoodMSc", degree_required_at_application=L.BACHELOR, deadline=datetime(2027, 1, 10)),
        entry("MscNeedsMasterX", degree_required_at_application=L.MASTER),
        entry("Unfunded", funding=FundingType.UNKNOWN, degree_required_at_application=L.BACHELOR),
        entry("Unverified", ver=V.UNVERIFIED, degree_required_at_application=L.BACHELOR),
        entry("PaidIntern", Category.INTERNSHIP, degree_required_at_application=L.BACHELOR),
        entry("DirectPhd", Category.PHD, degree_required_at_application=L.BACHELOR),
        entry("PhdBlockedY", Category.PHD, degree_required_at_application=L.MASTER),
    ]
    r = report(es)
    head = r.split("━━ ۵.")[0]
    assert "GoodMSc" in head and "PaidIntern" in head and "DirectPhd" in head
    for bad in ("MscNeedsMasterX", "Unfunded", "Unverified"):
        assert bad not in head                      # never actionable
    rej = r.split("━━ ۵.")[1]
    assert "MscNeedsMasterX" in rej and "تأمین مالی تأییدشده وجود ندارد" in rej and "تأییدشده در دسترس نیست" in rej
    assert "در حال حاضر واجد شرایط نیستید" in head and "PhdBlockedY" in head.split("در حال حاضر")[1]


def test_urgent_deadline_and_date_only_disclaimer():
    r = report([entry("Soon", degree_required_at_application=L.BACHELOR, deadline=datetime(2026, 11, 15))])
    urgent = r.split("━━ ۴.")[1].split("━━ ۵.")[0]
    assert "فردا" in urgent and "Soon" in urgent
    assert "فقط تاریخ" in r


def test_expired_deadline_rejected():
    r = report([entry("Old", degree_required_at_application=L.BACHELOR, deadline=datetime(2026, 11, 1))])
    assert "Old" in r.split("━━ ۵.")[1] and "مهلت درخواست گذشته" in r


def test_failed_sources_reported():
    r = report([], SearchSummary(["a"], {"b": "timeout"}))
    assert "b (timeout)" in r
