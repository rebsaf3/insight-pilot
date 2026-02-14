"""Usage Analytics — workspace-level usage data with filterable charts."""

import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta

from auth.session import require_auth, get_current_workspace
from config.settings import CHART_PALETTES
from db import queries

# Design tokens (match theme.py)
_COLORS = CHART_PALETTES["default"]  # ["#2D3FE0", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"]
_CHART_LAYOUT = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    xaxis=dict(gridcolor="#F3F4F6"),
    yaxis=dict(gridcolor="#F3F4F6"),
    margin=dict(l=20, r=20, t=30, b=20),
    font=dict(family="Inter, sans-serif"),
)


def show():
    user = require_auth()
    ws = get_current_workspace()
    if not ws:
        st.warning("Please select a workspace.")
        st.stop()

    st.title("Usage Analytics")

    # --- Filters ---
    start_str, end_str, project_id, member_id = _render_filters(ws)

    # --- Summary KPIs ---
    _render_kpis(ws.id, start_str, end_str, project_id, member_id)

    st.divider()

    # --- Chart row 1 ---
    col_left, col_right = st.columns(2)
    with col_left:
        _render_credit_usage_chart(ws.id, start_str, end_str, member_id)
    with col_right:
        _render_analysis_activity_chart(ws.id, start_str, end_str, project_id, member_id)

    st.divider()

    # --- Chart row 2 ---
    col_left2, col_right2 = st.columns(2)
    with col_left2:
        _render_token_usage_by_project(ws.id, start_str, end_str, member_id)
    with col_right2:
        _render_file_upload_summary(ws.id, start_str, end_str, project_id)

    st.divider()

    # --- Activity Log ---
    _render_activity_log(ws.id, start_str, end_str, project_id, member_id)


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

def _render_filters(ws):
    """Render the filter bar. Returns (start_date_str, end_date_str, project_id, member_id)."""
    # Determine how many filter columns we need
    members = queries.get_workspace_members(ws.id)
    has_members = len(members) > 1

    if has_members:
        filter_cols = st.columns([2, 2, 2, 2])
    else:
        filter_cols = st.columns([2, 2, 2])

    # Date range preset
    with filter_cols[0]:
        date_preset = st.selectbox(
            "Date Range",
            ["Last 7 days", "Last 30 days", "Last 90 days", "Custom"],
            index=1,
            key="usage_date_preset",
        )

    today = datetime.now().date()
    if date_preset == "Last 7 days":
        start_date, end_date = today - timedelta(days=7), today
    elif date_preset == "Last 30 days":
        start_date, end_date = today - timedelta(days=30), today
    elif date_preset == "Last 90 days":
        start_date, end_date = today - timedelta(days=90), today
    else:
        with filter_cols[1]:
            date_range = st.date_input(
                "Select Range",
                value=(today - timedelta(days=30), today),
                key="usage_custom_range",
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date, end_date = today - timedelta(days=30), today

    # Project filter
    proj_col_idx = 2 if date_preset == "Custom" else 1
    with filter_cols[proj_col_idx]:
        projects = queries.get_projects_for_workspace(ws.id)
        project_options = {"__all__": "All Projects"}
        project_options.update({p.id: p.name for p in projects})
        selected_project = st.selectbox(
            "Project",
            list(project_options.keys()),
            format_func=lambda k: project_options[k],
            key="usage_project_filter",
        )
    project_id = None if selected_project == "__all__" else selected_project

    # Member filter (only if workspace has multiple members)
    member_id = None
    if has_members:
        member_col_idx = 3 if date_preset == "Custom" else 2
        with filter_cols[member_col_idx]:
            member_options = {"__all__": "All Members"}
            for m in members:
                member_user = queries.get_user_by_id(m.user_id)
                if member_user:
                    member_options[m.user_id] = member_user.display_name
            selected_member = st.selectbox(
                "Member",
                list(member_options.keys()),
                format_func=lambda k: member_options[k],
                key="usage_member_filter",
            )
            member_id = None if selected_member == "__all__" else selected_member

    return start_date.isoformat(), end_date.isoformat(), project_id, member_id


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

def _render_kpis(workspace_id, start_date, end_date, project_id, member_id):
    """Render the 4 summary KPI metric cards."""
    credits_used = queries.get_credits_used_in_range(workspace_id, start_date, end_date, member_id)
    analyses_run = queries.get_analyses_count_in_range(workspace_id, start_date, end_date, project_id, member_id)
    uploads = queries.get_uploads_in_range(workspace_id, start_date, end_date, project_id, member_id)
    files_uploaded = len(uploads)
    dashboards_created = queries.get_dashboards_created_in_range(
        workspace_id, start_date, end_date, project_id, member_id,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Credits Used", f"{credits_used:,}")
    col2.metric("AI Analyses", f"{analyses_run:,}")
    col3.metric("Files Uploaded", f"{files_uploaded:,}")
    col4.metric("Dashboards Created", f"{dashboards_created:,}")


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _render_credit_usage_chart(workspace_id, start_date, end_date, member_id):
    """Area chart of daily credit consumption."""
    st.subheader("Credit Usage Over Time")

    data = queries.get_credit_usage_by_day(workspace_id, start_date, end_date, member_id)
    if not data:
        st.info("No credit usage in this period.")
        return

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    fig = px.area(
        df, x="date", y="credits_used",
        labels={"date": "Date", "credits_used": "Credits Used"},
        color_discrete_sequence=[_COLORS[0]],
    )
    fig.update_layout(**_CHART_LAYOUT, hovermode="x unified")
    fig.update_traces(
        fill="tozeroy",
        fillcolor="rgba(45, 63, 224, 0.1)",
        line=dict(width=2),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_analysis_activity_chart(workspace_id, start_date, end_date, project_id, member_id):
    """Bar chart of analyses per day."""
    st.subheader("AI Analysis Activity")

    data = queries.get_analyses_by_day(workspace_id, start_date, end_date, project_id, member_id)
    if not data:
        st.info("No analysis activity in this period.")
        return

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    fig = px.bar(
        df, x="date", y="analysis_count",
        labels={"date": "Date", "analysis_count": "Analyses"},
        color_discrete_sequence=[_COLORS[1]],
    )
    fig.update_layout(**_CHART_LAYOUT, bargap=0.3)
    st.plotly_chart(fig, use_container_width=True)


def _render_token_usage_by_project(workspace_id, start_date, end_date, member_id):
    """Horizontal bar chart of token usage broken down by project."""
    st.subheader("Usage by Project")

    data = queries.get_token_usage_by_project(workspace_id, start_date, end_date, member_id)
    if not data:
        st.info("No project usage data in this period.")
        return

    df = pd.DataFrame(data)

    fig = px.bar(
        df, x="total_tokens", y="project_name",
        orientation="h",
        labels={"total_tokens": "Tokens Used", "project_name": "Project"},
        color_discrete_sequence=[_COLORS[4]],
        text="analysis_count",
    )
    fig.update_traces(texttemplate="%{text} analyses", textposition="auto")
    fig.update_layout(**_CHART_LAYOUT, yaxis=dict(autorange="reversed", gridcolor="#F3F4F6"))
    st.plotly_chart(fig, use_container_width=True)


def _render_file_upload_summary(workspace_id, start_date, end_date, project_id):
    """Donut chart of file format distribution."""
    st.subheader("File Upload Summary")

    data = queries.get_file_format_distribution(workspace_id, start_date, end_date, project_id)
    if not data:
        st.info("No file uploads in this period.")
        return

    df = pd.DataFrame(data)

    fig = px.pie(
        df, names="file_format", values="count",
        color_discrete_sequence=_COLORS,
        hole=0.4,
    )
    fig.update_layout(
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=30, b=20),
        font=dict(family="Inter, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15),
    )
    fig.update_traces(textinfo="label+percent", textfont_size=12)
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Activity Log
# ---------------------------------------------------------------------------

def _render_activity_log(workspace_id, start_date, end_date, project_id, member_id):
    """Scrollable list of recent activity."""
    st.subheader("Activity Log")

    activities = queries.get_recent_activity(
        workspace_id, start_date, end_date,
        project_id=project_id, user_id=member_id, limit=50,
    )

    if not activities:
        st.info("No activity in this period.")
        return

    # Cache user display names to avoid N+1 queries
    _user_cache: dict[str, str] = {}

    def _get_name(uid: str) -> str:
        if uid not in _user_cache:
            u = queries.get_user_by_id(uid)
            _user_cache[uid] = u.display_name if u else "Unknown"
        return _user_cache[uid]

    for activity in activities:
        col1, col2, col3, col4 = st.columns([0.5, 4, 2, 2])

        with col1:
            if activity["activity_type"] == "credit":
                st.markdown(":material/payments:")
            else:
                st.markdown(":material/analytics:")

        with col2:
            desc = activity["description"] or ""
            if activity["activity_type"] == "analysis":
                desc = f"AI Analysis: {desc}..."
            st.markdown(desc)

        with col3:
            st.caption(_get_name(activity["user_id"]))

        with col4:
            ts = activity["created_at"][:16]  # YYYY-MM-DD HH:MM
            st.caption(ts)


show()
