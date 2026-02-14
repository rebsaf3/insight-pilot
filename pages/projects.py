"""Projects page — list, create, and edit projects in the current workspace."""

import streamlit as st

from auth.session import require_auth, get_current_workspace, set_current_workspace, set_current_project
from services.workspace_service import get_user_workspaces
from db import queries


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

    st.title(f"Projects — {ws.name}")

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

    # List projects
    projects = queries.get_projects_for_workspace(ws.id)
    if not projects:
        st.info("No projects yet. Create one above to get started.")
        return

    for project in projects:
        col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
        with col1:
            if st.button(
                f"**{project.name}**\n\n{project.description or 'No description'}",
                key=f"proj_{project.id}",
                use_container_width=True,
            ):
                set_current_project(project.id)
                st.switch_page("pages/upload.py")
        with col2:
            files = queries.get_files_for_project(project.id)
            st.metric("Files", len(files))
        with col3:
            dashboards = queries.get_dashboards_for_project(project.id)
            st.metric("Dashboards", len(dashboards))
        with col4:
            if st.button("Edit", key=f"edit_{project.id}"):
                st.session_state[f"editing_project_{project.id}"] = True

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
