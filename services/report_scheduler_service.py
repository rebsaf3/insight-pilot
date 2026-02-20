"""Scheduled report service: scheduling logic + delivery execution."""

from datetime import datetime, timedelta
import calendar

from db import queries
from services.export_service import export_dashboard_as_excel, export_dashboard_as_pdf
from services.notification_service import send_email


_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


def _utcnow() -> datetime:
    return datetime.utcnow().replace(second=0, microsecond=0)


def _parse_send_time(send_time_utc: str) -> tuple[int, int]:
    hh, mm = send_time_utc.split(":", 1)
    return int(hh), int(mm)


def compute_next_run_at(
    frequency: str,
    send_time_utc: str,
    day_of_week: int | None = None,
    day_of_month: int | None = None,
    now_utc: datetime | None = None,
) -> str:
    now = now_utc or _utcnow()
    hour, minute = _parse_send_time(send_time_utc)

    if frequency == "daily":
        candidate = now.replace(hour=hour, minute=minute)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate.strftime(_DATETIME_FMT)

    if frequency == "weekly":
        dow = 0 if day_of_week is None else int(day_of_week)
        today = now.weekday()
        offset = (dow - today) % 7
        candidate = now.replace(hour=hour, minute=minute) + timedelta(days=offset)
        if candidate <= now:
            candidate += timedelta(days=7)
        return candidate.strftime(_DATETIME_FMT)

    if frequency == "monthly":
        dom = max(1, min(31, int(day_of_month or 1)))
        year, month = now.year, now.month
        last_day = calendar.monthrange(year, month)[1]
        candidate_day = min(dom, last_day)
        candidate = now.replace(day=candidate_day, hour=hour, minute=minute)
        if candidate <= now:
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1
            last_day = calendar.monthrange(year, month)[1]
            candidate_day = min(dom, last_day)
            candidate = candidate.replace(year=year, month=month, day=candidate_day)
        return candidate.strftime(_DATETIME_FMT)

    raise ValueError(f"Unsupported frequency: {frequency}")


def create_schedule(
    workspace_id: str,
    dashboard_id: str,
    created_by: str,
    name: str,
    recipient_emails: list[str],
    frequency: str,
    send_time_utc: str,
    day_of_week: int | None,
    day_of_month: int | None,
    include_pdf: bool,
    include_excel: bool,
) -> str:
    next_run_at = compute_next_run_at(
        frequency=frequency,
        send_time_utc=send_time_utc,
        day_of_week=day_of_week,
        day_of_month=day_of_month,
    )
    return queries.create_scheduled_report(
        workspace_id=workspace_id,
        dashboard_id=dashboard_id,
        created_by=created_by,
        name=name,
        recipient_emails=recipient_emails,
        frequency=frequency,
        send_time_utc=send_time_utc,
        day_of_week=day_of_week,
        day_of_month=day_of_month,
        include_pdf=include_pdf,
        include_excel=include_excel,
        next_run_at=next_run_at,
    )


def send_scheduled_report(report_id: str, force: bool = False) -> tuple[bool, str]:
    report = queries.get_scheduled_report_by_id(report_id)
    if not report:
        return False, "Scheduled report not found."

    now = _utcnow()
    if not force and not report.active:
        return False, "Schedule is inactive."

    dashboard = queries.get_dashboard_by_id(report.dashboard_id)
    if not dashboard:
        queries.mark_scheduled_report_failed(report.id, "Dashboard not found")
        return False, "Dashboard not found."

    charts = queries.get_charts_for_dashboard(report.dashboard_id)
    attachments: list[tuple[str, bytes, str]] = []

    try:
        if report.include_pdf:
            pdf = export_dashboard_as_pdf(dashboard, charts)
            attachments.append((f"{dashboard.name}.pdf", pdf, "application/pdf"))
        if report.include_excel:
            xlsx = export_dashboard_as_excel(dashboard, charts)
            attachments.append(
                (
                    f"{dashboard.name}.xlsx",
                    xlsx,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            )

        subject = f"Scheduled Report: {report.name}"
        body = (
            f"Your scheduled report for dashboard '{dashboard.name}' is ready.\n\n"
            f"Generated at (UTC): {now.strftime(_DATETIME_FMT)}\n"
            f"Frequency: {report.frequency}\n"
        )

        ok, msg = send_email(report.recipient_emails, subject, body, attachments=attachments)
        if not ok:
            queries.mark_scheduled_report_failed(report.id, msg)
            return False, msg

        next_run = compute_next_run_at(
            report.frequency,
            report.send_time_utc,
            day_of_week=report.day_of_week,
            day_of_month=report.day_of_month,
            now_utc=now,
        )
        queries.mark_scheduled_report_sent(report.id, next_run)
        return True, "Report sent."
    except Exception as e:
        queries.mark_scheduled_report_failed(report.id, str(e))
        return False, str(e)


def run_due_reports(limit: int = 20) -> dict:
    now = _utcnow().strftime(_DATETIME_FMT)
    due = queries.get_due_scheduled_reports(now_utc=now, limit=limit)
    sent = 0
    failed = 0
    for report in due:
        ok, _ = send_scheduled_report(report.id)
        if ok:
            sent += 1
        else:
            failed += 1
    return {"checked": len(due), "sent": sent, "failed": failed}
