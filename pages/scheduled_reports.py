"""Scheduled reports management page."""

from datetime import time

import streamlit as st

from auth.session import require_permission
from db import queries
from services import report_scheduler_service


def _workspace_dashboards(workspace_id: str):
    choices = {}
    for project in queries.get_projects_for_workspace(workspace_id):
        dashboards = queries.get_dashboards_for_project(project.id)
        for dash in dashboards:
            choices[dash.id] = f"{project.name} / {dash.name}"
    return choices


def show():
    user, ws = require_permission("create_edit_dashboards")
    st.title("Scheduled Reports")
    st.caption("Send dashboard snapshots on a recurring schedule via email.")

    with st.expander("Run Pending Schedules", expanded=False):
        if st.button("Process Due Reports Now", use_container_width=True):
            result = report_scheduler_service.run_due_reports(limit=25)
            st.success(
                f"Checked {result['checked']} schedule(s): {result['sent']} sent, {result['failed']} failed."
            )

    dashboards = _workspace_dashboards(ws.id)
    if not dashboards:
        st.info("Create at least one dashboard before scheduling reports.")
        return

    st.subheader("Create Schedule")
    with st.form("create_schedule"):
        schedule_name = st.text_input("Schedule Name", placeholder="Weekly Executive Dashboard")
        dashboard_id = st.selectbox(
            "Dashboard",
            list(dashboards.keys()),
            format_func=lambda k: dashboards[k],
        )
        recipients = st.text_input(
            "Recipients (comma-separated emails)",
            value=user.email,
            help="Example: lead@company.com, exec@company.com",
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly"])
        with col2:
            send_time = st.time_input("Send Time (UTC)", value=time(9, 0))
        with col3:
            if frequency == "weekly":
                day_of_week = st.selectbox(
                    "Day of Week",
                    list(range(7)),
                    format_func=lambda d: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d],
                )
                day_of_month = None
            elif frequency == "monthly":
                day_of_month = st.number_input("Day of Month", min_value=1, max_value=31, value=1, step=1)
                day_of_week = None
            else:
                day_of_week = None
                day_of_month = None

        include_pdf = st.checkbox("Attach PDF", value=True)
        include_excel = st.checkbox("Attach Excel", value=True)

        submitted = st.form_submit_button("Create Schedule", use_container_width=True)

    if submitted:
        emails = [e.strip().lower() for e in recipients.split(",") if e.strip()]
        if not schedule_name:
            st.error("Schedule name is required.")
        elif not emails:
            st.error("Provide at least one recipient email.")
        elif not include_pdf and not include_excel:
            st.error("Select at least one attachment format.")
        else:
            send_time_utc = send_time.strftime("%H:%M")
            report_scheduler_service.create_schedule(
                workspace_id=ws.id,
                dashboard_id=dashboard_id,
                created_by=user.id,
                name=schedule_name,
                recipient_emails=emails,
                frequency=frequency,
                send_time_utc=send_time_utc,
                day_of_week=day_of_week,
                day_of_month=day_of_month,
                include_pdf=include_pdf,
                include_excel=include_excel,
            )
            st.success("Scheduled report created.")
            st.rerun()

    st.divider()
    st.subheader("Existing Schedules")
    schedules = queries.get_scheduled_reports_for_workspace(ws.id)
    if not schedules:
        st.info("No scheduled reports yet.")
        return

    for report in schedules:
        dash = queries.get_dashboard_by_id(report.dashboard_id)
        dash_name = dash.name if dash else "(missing dashboard)"
        with st.container(border=True):
            st.markdown(f"**{report.name}**")
            st.caption(
                f"Dashboard: {dash_name} | Frequency: {report.frequency} | Next run (UTC): {report.next_run_at}"
            )
            st.caption(f"Recipients: {', '.join(report.recipient_emails)}")
            if report.last_error:
                st.error(f"Last error: {report.last_error}")

            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                active = st.toggle("Active", value=report.active, key=f"active_{report.id}")
                if active != report.active:
                    queries.update_scheduled_report(report.id, active=active)
                    st.rerun()
            with c2:
                if st.button("Send Now", key=f"send_{report.id}"):
                    ok, msg = report_scheduler_service.send_scheduled_report(report.id, force=True)
                    if ok:
                        st.success("Report sent.")
                    else:
                        st.error(f"Send failed: {msg}")
                    st.rerun()
            with c3:
                if st.button("Delete", key=f"del_{report.id}", type="secondary"):
                    queries.delete_scheduled_report(report.id)
                    st.success("Schedule deleted.")
                    st.rerun()


show()
