"""Projects page — list and create projects in the current workspace."""

import streamlit as st

from auth.session import require_auth, get_current_workspace, set_current_workspace, set_current_project
from services.workspace_service import get_user_workspaces
from db import queries
from components.sidebar import render_sidebar


def show():
    user = require_auth()
    render_sidebar(user)

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
            submitted = st.form_submit_button("Create Project", use_container_width=True)
        if submitted and name:
            queries.create_project(workspace_id=ws.id, created_by=user.id, name=name, description=description)
            st.success(f"Project '{name}' created!")
            st.rerun()

    # List projects
    projects = queries.get_projects_for_workspace(ws.id)
    if not projects:
        st.info("No projects yet. Create one above to get started.")
        return

    for project in projects:
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            if st.button(f"**{project.name}**\n\n{project.description or 'No description'}", key=f"proj_{project.id}", use_container_width=True):
                set_current_project(project.id)
                st.switch_page("pages/upload.py")
        with col2:
            files = queries.get_files_for_project(project.id)
            st.metric("Files", len(files))
        with col3:
            dashboards = queries.get_dashboards_for_project(project.id)
            st.metric("Dashboards", len(dashboards))


show()
