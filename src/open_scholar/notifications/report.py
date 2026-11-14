"""Persian daily report (MISSION.md section 9.1). Pure formatting, no I/O.

Rules enforced here:
* unverified / closed / withdrawn / expired opportunities are never actionable;
* hard-ineligible opportunities appear only under "rejected" with reasons;
* date-only deadlines are never presented as exact closing times;
* nothing is fabricated: missing data is printed as "نامشخص" (unknown).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

from open_scholar.core.opportunity import (Category, FundingType, OpportunityRecord,
                                           VerificationStatus)
from open_scholar.eligibility.engine import EligibilityDecision, EligibilityStatus

UNKNOWN = "نامشخص"
MAX_REJECTED = 5
URGENT_DAYS = 7

STATUS_FA = {
    EligibilityStatus.ELIGIBLE: "واجد شرایط",
    EligibilityStatus.LIKELY_ELIGIBLE: "احتمالاً واجد شرایط",
    EligibilityStatus.UNCERTAIN: "نامشخص (نیاز به بررسی)",
    EligibilityStatus.NOT_ELIGIBLE: "فاقد شرایط",
}
FUNDING_FA = {FundingType.FULL: "کامل", FundingType.PARTIAL: "جزئی",
              FundingType.NONE: "ندارد", FundingType.UNKNOWN: UNKNOWN}
REJECT_FA = {
    "degree_at_application": "مدرک تکمیل‌شده لازم است (مدرک در حال تحصیل کافی نیست)",
    "active_enrollment": "دانشجوی فعال بودن لازم است ولی احراز نشد",
    "previous_enrollment": "سابقهٔ ثبت‌نام قبلی مجاز نیست",
    "completed_degree_excluded": "دارندگان این مدرک پذیرفته نمی‌شوند",
    "nationality": "محدودیت تابعیت",
    "gpa": "معدل کمتر از حداقل",
    "opportunity_open": "درخواست بسته یا لغو شده است",
}


@dataclass
class ReportEntry:
    opp: OpportunityRecord
    decision: EligibilityDecision


@dataclass
class SearchSummary:
    sources_checked: list[str] = field(default_factory=list)
    sources_failed: dict[str, str] = field(default_factory=dict)
    new_count: int = 0
    pages_fetched: int = 0
    pages_failed: dict[str, str] = field(default_factory=dict)
    extraction_methods: list[str] = field(default_factory=list)  # "rules" or "llm:<provider>:<model>"


def days_left(opp: OpportunityRecord, today: date, tz: ZoneInfo) -> int | None:
    if opp.deadline is None:
        return None
    d = opp.deadline.astimezone(tz).date() if opp.deadline_has_time and opp.deadline.tzinfo \
        else opp.deadline.date()
    return (d - today).days


def format_deadline(opp: OpportunityRecord, tz: ZoneInfo) -> str:
    if opp.deadline is None:
        return UNKNOWN
    if opp.deadline_has_time and opp.deadline.tzinfo:
        return opp.deadline.astimezone(tz).strftime("%Y-%m-%d %H:%M") + f" ({tz.key})"
    return opp.deadline.strftime("%Y-%m-%d") + " (فقط تاریخ؛ ساعت دقیق بسته‌شدن تأیید نشده)"


def _v(x) -> str:
    return str(x) if x not in (None, "") else UNKNOWN


PHD_C_HOLDER = ("نیازمند مدرک کارشناسی ارشد تکمیل‌شده (شما از قبل دارید) — ورود مستقیم دکتری نیست "
                "(Requires a completed Master's degree (You already hold one))")


def _reject_reasons(e: ReportEntry, left: int | None, holder: bool = False) -> list[str]:
    o = e.opp
    reasons = [REJECT_FA.get(c.code, c.explanation) for c in e.decision.failed]
    if o.verification_status == VerificationStatus.UNVERIFIED:
        reasons.append("اطلاعات رسمی تأییدشده در دسترس نیست")
    if left is not None and left < 0:
        reasons.append("مهلت درخواست گذشته است")
    if o.category == Category.PHD and o.phd_entry_category == "C":
        reasons.append(PHD_C_HOLDER if holder else "مدرک کارشناسی ارشد تکمیل‌شده در زمان درخواست لازم است")
    if o.category == Category.PHD and o.phd_entry_category is None:
        reasons.append("شرط مدرک ورود مستقیم دکتری تأیید نشده است")
    if o.category in (Category.MASTERS, Category.INTERNSHIP):
        paid = o.funding_type in (FundingType.FULL, FundingType.PARTIAL) or \
            (o.category == Category.INTERNSHIP and bool(o.stipend))
        if not paid:
            reasons.append("تأمین مالی تأییدشده وجود ندارد")
    return list(dict.fromkeys(reasons))  # de-duplicate, keep order


def _common_tail(o: OpportunityRecord, e: ReportEntry, tz: ZoneInfo) -> list[str]:
    score = "-" if e.decision.match_score is None else f"{e.decision.match_score:.0f}/100"
    return [f"  • وضعیت شرایط: {STATUS_FA[e.decision.status]} | امتیاز تطابق: {score}",
            f"  • مهلت: {format_deadline(o, tz)}",
            f"  • منبع رسمی: {_v(o.official_url)}",
            f"  • لینک درخواست: {_v(o.application_url)}"]


def _fmt_masters(e: ReportEntry, tz) -> str:
    o = e.opp
    return "\n".join([f"▪ {o.title}",
                      f"  • دانشگاه: {_v(o.organization)} | کشور: {_v(o.country)}",
                      f"  • نوع تأمین مالی: {FUNDING_FA[o.funding_type]} | شهریه: {_v(o.tuition_coverage)}"
                      f" | حقوق/هزینهٔ زندگی: {_v(o.stipend)}",
                      f"  • شرایط پذیرش: {_v(o.requirements.degree_required_at_application and o.requirements.degree_required_at_application.value)}",
                      *_common_tail(o, e, tz)])


def _fmt_internship(e: ReportEntry, tz) -> str:
    o = e.opp
    r = o.requirements
    status_req = "دانشجوی فعال لازم است" if r.active_enrollment_required else (
        UNKNOWN if r.active_enrollment_required is None else "دانشجوی فعال لازم نیست")
    return "\n".join([f"▪ {o.title}",
                      f"  • سازمان: {_v(o.organization)} | کشور: {_v(o.country)}",
                      f"  • حقوق/استایپند: {_v(o.stipend)} | مدت: {_v(o.duration)} | شروع: {_v(o.start_date)}",
                      f"  • شرط وضعیت دانشجویی: {status_req}",
                      *_common_tail(o, e, tz)])


def _fmt_phd(e: ReportEntry, tz) -> str:
    o = e.opp
    cat = o.phd_entry_category
    bach = {"A": "بله (کارشناسی در زمان درخواست کافی است)",
            "B": "بله، ولی کارشناسی ارشد باید پیش از ثبت‌نام تکمیل شود"}.get(cat, UNKNOWN)
    return "\n".join([f"▪ {o.title}",
                      f"  • دانشگاه: {_v(o.organization)} | کشور: {_v(o.country)}",
                      f"  • موضوع: {_v(o.field)} | تأمین مالی: {FUNDING_FA[o.funding_type]}",
                      f"  • پذیرش فقط با کارشناسی: {bach}",
                      *_common_tail(o, e, tz)])


def build_daily_report(entries: list[ReportEntry], summary: SearchSummary, now: datetime,
                       tz_name: str = "UTC") -> str:
    tz = ZoneInfo(tz_name)
    today = now.astimezone(tz).date()

    masters, interns, phds, urgent, rejected, not_elig_phd = [], [], [], [], [], []
    for e in entries:
        o, left = e.opp, days_left(e.opp, today, tz)
        reasons = _reject_reasons(e, left)
        hard = e.decision.status == EligibilityStatus.NOT_ELIGIBLE or bool(reasons)
        if o.category == Category.PHD and o.phd_entry_category == "C":
            # Category C is never a direct-entry opportunity. Show it separately only when the
            # user is actually blocked by the master's requirement and the posting is live.
            blocked = any(c.code == "degree_at_application" for c in e.decision.failed)
            live = o.verification_status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED) \
                and (left is None or left >= 0)
            if blocked and live:
                not_elig_phd.append(e)
            elif live:
                # User already holds the Master's: still not a direct-entry PhD -> rejected section.
                rejected.append((e, _reject_reasons(e, left, holder=True)))
            else:
                rejected.append((e, reasons))
            continue
        if hard:
            rejected.append((e, reasons))
            continue
        {Category.MASTERS: masters, Category.INTERNSHIP: interns, Category.PHD: phds}[o.category].append(e)
        if left is not None and 0 <= left <= URGENT_DAYS:
            urgent.append((e, left))

    out = [f"📋 گزارش روزانهٔ OpenScholar — {today.isoformat()}", ""]

    def section(title: str, items: list[ReportEntry], fmt):
        out.append(f"━━ {title} ━━")
        out.extend(fmt(e, tz) for e in items) if items else out.append("موردی که شرایط تأیید و واجد‌شرایط بودن را داشته باشد یافت نشد.")
        out.append("")

    section("۱. کارشناسی ارشد با تأمین مالی", masters, _fmt_masters)
    section("۲. کارآموزی با حقوق", interns, _fmt_internship)
    section("۳. دکتری با ورود مستقیم", phds, _fmt_phd)
    if not_elig_phd:
        out.append("در حال حاضر واجد شرایط نیستید: مدرک کارشناسی ارشد تکمیل‌شده لازم است")
        out.extend(f"  - {e.opp.title} ({_v(e.opp.organization)})" for e in not_elig_phd)
        out.append("")

    out.append("━━ ۴. مهلت‌های فوری ━━")
    if urgent:
        for e, left in sorted(urgent, key=lambda x: x[1]):
            when = "امروز" if left == 0 else "فردا" if left == 1 else f"{left} روز دیگر"
            out.append(f"⏰ {when}: {e.opp.title} — {format_deadline(e.opp, tz)}")
    else:
        out.append("مهلت فوری (تا ۷ روز آینده) وجود ندارد.")
    out.append("")

    out.append("━━ ۵. موارد ردشده ━━")
    if rejected:
        for e, reasons in rejected[:MAX_REJECTED]:
            out.append(f"✖ {e.opp.title} — دلیل: {'؛ '.join(reasons) or UNKNOWN}")
        if len(rejected) > MAX_REJECTED:
            out.append(f"... و {len(rejected) - MAX_REJECTED} مورد دیگر")
    else:
        out.append("موردی وجود ندارد.")
    out.append("")

    out.append("━━ ۶. خلاصهٔ جستجو ━━")
    out.append(f"منابع بررسی‌شده: {', '.join(summary.sources_checked) or 'هیچ'}")
    if summary.sources_failed:
        out.append("منابع ناموفق: " + "؛ ".join(f"{k} ({v})" for k, v in summary.sources_failed.items()))
    if summary.pages_fetched or summary.pages_failed:
        meth = ", ".join(summary.extraction_methods) or "-"
        out.append(f"صفحات بررسی‌شده: {summary.pages_fetched} | ناموفق: {len(summary.pages_failed)} | روش استخراج: {meth}")
    out.append("توجه: پوشش جستجو کامل یا جهانی نیست؛ فقط منابع بالا بررسی شده‌اند.")
    actionable = len(masters) + len(interns) + len(phds)
    if actionable == 0:
        out.append("امروز فرصت جدیدی که شرایط تأیید و واجد‌شرایط بودن شما را داشته باشد یافت نشد.")
        out.append("(No new opportunities meeting your eligibility and verification requirements were found today.)")
    else:
        out.append(f"فرصت‌های قابل اقدام: {actionable} | موارد جدید: {summary.new_count}")
    return "\n".join(out)
