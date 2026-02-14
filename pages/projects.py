"""Projects page — list, create, and edit projects in the current workspace.

Uses a rich card layout with per-project analytics (files, dashboards,
analyses) and file status badges.
"""

import streamlit as st
from datetime import datetime, timezone

from auth.session import require_auth, get_current_workspace, set_current_workspace, set_current_project
from services.workspace_service import get_user_workspaces
from db import queries


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _time_ago(iso_str: str | None) -> str:
    """Convert an ISO-8601 timestamp to a human-readable relative string."""
    if not iso_str:
        return "No activity"
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        secs = int(delta.total_seconds())
        if secs < 60:
            return "Just now"
        if secs < 3600:
            mins = secs // 60
            return f"{mins}m ago"
        if secs < 86400:
            hrs = secs // 3600
            return f"{hrs}h ago"
        days = secs // 86400
        if days < 30:
            return f"{days}d ago"
        months = days // 30
        return f"{months}mo ago"
    except (ValueError, TypeError):
        return "—"


def _status_badge(status: str) -> str:
    """Return an HTML badge for file upload status."""
    mapping = {
        "success": ("ip-badge ip-badge-success", "Success"),
        "error":   ("ip-badge ip-badge-error",   "Error"),
        "pending": ("ip-badge ip-badge-pending",  "Pending"),
    }
    cls, label = mapping.get(status, ("ip-badge ip-badge-info", status.title()))
    return f"<span class='{cls}'>{label}</span>"


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

def show():
    user = require_auth()

    # Auto-select workspace if none selected
    ws = get_current_workspace()
    if not ws:
        workspaces = get_user_workspaces(user.id)
        if workspaces:
            set_current_workspace(workspaces[0].id)
            ws = workspaces[0]
        else:
            st.warning("No workspace found. This shouldn't happen — please contact support.")
            st.stop()

    st.title(f"Projects")
    st.caption(f"Workspace: {ws.name}")

    # Create new project
    with st.expander("Create New Project", icon=":material/add:"):
        with st.form("new_project"):
            name = st.text_input("Project Name", placeholder="Q4 Sales Analysis")
            description = st.text_area("Description (optional)", placeholder="Analysis of Q4 2025 sales data")
            instructions = st.text_area(
                "AI Instructions (optional)",
                placeholder="Always use blue color scheme. Revenue is in EUR. Fiscal year starts in April.",
                help="These instructions will be automatically applied to ALL AI analyses in this project.",
                height=100,
            )
            submitted = st.form_submit_button("Create Project", use_container_width=True)
        if submitted and name:
            queries.create_project(
                workspace_id=ws.id, created_by=user.id,
                name=name, description=description, instructions=instructions,
            )
            st.success(f"Project '{name}' created!")
            st.rerun()

    st.divider()

    # List projects as rich cards
    projects = queries.get_projects_for_workspace(ws.id)
    if not projects:
        st.markdown(
            "<div class='ip-empty-state'>"
            "<div style='font-size:3rem;margin-bottom:0.5rem'>:material/folder_open:</div>"
            "<div style='font-size:1.1rem;font-weight:600;color:#1C1917;margin-bottom:0.25rem'>"
            "No projects yet</div>"
            "<div style='font-size:0.88rem'>Create your first project above to get started.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    for project in projects:
        summary = queries.get_project_activity_summary(project.id)
        last_activity = _time_ago(summary["last_activity"])

        # Card header row — project name + last activity + actions
        st.markdown(
            f"<div class='ip-card ip-card-hover' style='padding:0.75rem 1.25rem'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center'>"
            f"<div>"
            f"<div style='font-weight:700;font-size:1rem;color:#1C1917'>{project.name}</div>"
            f"<div style='font-size:0.82rem;color:#57534E;margin-top:2px'>"
            f"{project.description or 'No description'}</div>"
            f"</div>"
            f"<span class='ip-badge ip-badge-info'>{last_activity}</span>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Stat row under card
        s1, s2, s3, s4, s5, s6, s7 = st.columns([1, 1, 1, 1, 1, 1, 2])
        with s1:
            st.markdown(
                f"<div class='ip-stat'><div class='ip-stat-value'>{summary['files_total']}</div>"
                f"<div class='ip-stat-label'>Files</div></div>",
                unsafe_allow_html=True,
            )
        with s2:
            st.markdown(
                f"<div class='ip-stat'><div class='ip-stat-value' style='color:#059669'>"
                f"{summary['files_success']}</div>"
                f"<div class='ip-stat-label'>Success</div></div>",
                unsafe_allow_html=True,
            )
        with s3:
            err_color = "#DC2626" if summary["files_error"] > 0 else "#A8A29E"
            st.markdown(
                f"<div class='ip-stat'><div class='ip-stat-value' style='color:{err_color}'>"
                f"{summary['files_error']}</div>"
                f"<div class='ip-stat-label'>Errors</div></div>",
                unsafe_allow_html=True,
            )
        with s4:
            st.markdown(
                f"<div class='ip-stat'><div class='ip-stat-value'>{summary['analyses_count']}</div>"
                f"<div class='ip-stat-label'>Analyses</div></div>",
                unsafe_allow_html=True,
            )
        with s5:
            st.markdown(
                f"<div class='ip-stat'><div class='ip-stat-value'>{summary['dashboards_count']}</div>"
                f"<div class='ip-stat-label'>Dashboards</div></div>",
                unsafe_allow_html=True,
            )
        with s6:
            if st.button("Edit", key=f"edit_{project.id}", use_container_width=True):
                st.session_state[f"editing_project_{project.id}"] = True
        with s7:
            if st.button(f"Open Project", key=f"open_{project.id}", type="primary", use_container_width=True):
                set_current_project(project.id)
                st.switch_page("pages/upload.py")

        # Inline edit form
        if st.session_state.get(f"editing_project_{project.id}"):
            with st.container(border=True):
                with st.form(f"edit_project_{project.id}"):
                    edit_name = st.text_input("Name", value=project.name)
                    edit_desc = st.text_area("Description", value=project.description)
                    edit_instructions = st.text_area(
                        "AI Instructions",
                        value=project.instructions or "",
                        placeholder="Always use blue color scheme. Revenue is in EUR.",
                        help="These instructions are automatically applied to ALL AI analyses in this project.",
                        height=100,
                    )
                    c1, c2 = st.columns(2)
                    save = c1.form_submit_button("Save", use_container_width=True, type="primary")
                    cancel = c2.form_submit_button("Cancel", use_container_width=True)
                if save and edit_name:
                    queries.update_project(
                        project.id, ws.id,
                        name=edit_name, description=edit_desc, instructions=edit_instructions,
                    )
                    st.session_state.pop(f"editing_project_{project.id}", None)
                    st.success("Project updated!")
                    st.rerun()
                if cancel:
                    st.session_state.pop(f"editing_project_{project.id}", None)
                    st.rerun()

                # Manage prompt templates for this project
                _show_prompt_templates(project, user)

                # Show file list with status badges
                _show_project_files(project.id)

        st.markdown("<div style='margin-bottom:0.25rem'></div>", unsafe_allow_html=True)


def _show_project_files(project_id: str) -> None:
    """Show files for a project with status badges."""
    files = queries.get_files_for_project(project_id)
    if not files:
        return

    st.markdown("**Uploaded Files:**")
    for f in files:
        size_mb = f.file_size_bytes / (1024 * 1024)
        row_info = f"{f.row_count:,} rows" if f.row_count else ""
        badge = _status_badge(getattr(f, "status", "success"))
        error_info = ""
        if getattr(f, "error_message", None):
            error_info = f"<div style='font-size:0.72rem;color:#DC2626;margin-top:2px'>{f.error_message}</div>"

        st.markdown(
            f"<div style='display:flex;align-items:center;gap:0.75rem;padding:0.4rem 0;"
            f"border-bottom:1px solid #F5F5F4;font-family:Inter,sans-serif'>"
            f"<div style='flex:1;font-size:0.85rem;font-weight:500'>{f.original_filename}"
            f"{error_info}</div>"
            f"<div style='font-size:0.75rem;color:#57534E'>{row_info}</div>"
            f"<div style='font-size:0.75rem;color:#A8A29E'>{size_mb:.1f} MB</div>"
            f"{badge}"
            f"</div>",
            unsafe_allow_html=True,
        )


def _show_prompt_templates(project, user):
    """Show and manage prompt templates for a project."""
    templates = queries.get_prompt_templates_for_project(project.id)
    if templates:
        st.markdown("**Saved Prompt Templates:**")
        for t in templates:
            tc1, tc2 = st.columns([5, 1])
            with tc1:
                st.caption(f"**{t.name}** — used {t.usage_count}x")
                st.text(t.prompt_text[:120] + ("..." if len(t.prompt_text) > 120 else ""))
            with tc2:
                if st.button("Delete", key=f"del_tmpl_{t.id}"):
                    queries.delete_prompt_template(t.id)
                    st.rerun()


show()
