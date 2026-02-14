"""Common sidebar component — workspace selector, user info, credit display."""

import streamlit as st

from auth.session import get_current_workspace, set_current_workspace, get_current_project_id
from config.settings import TIERS
from db import queries
from db.models import User
from services.workspace_service import get_user_workspaces


def render_sidebar(user: User) -> None:
    """Render the common sidebar with workspace selector and user info."""
    with st.sidebar:
        st.markdown(f"**{user.display_name}**")
        st.caption(user.email)

        st.divider()

        # Workspace selector
        workspaces = get_user_workspaces(user.id)
        if not workspaces:
            st.warning("No workspaces found.")
            return

        current_ws = get_current_workspace()
        current_idx = 0
        ws_names = []
        for i, ws in enumerate(workspaces):
            ws_names.append(ws.name)
            if current_ws and ws.id == current_ws.id:
                current_idx = i

        selected_name = st.selectbox(
            "Workspace",
            ws_names,
            index=current_idx,
            key="sidebar_ws_selector",
        )

        selected_ws = workspaces[ws_names.index(selected_name)]
        if not current_ws or selected_ws.id != current_ws.id:
            set_current_workspace(selected_ws.id)
            st.rerun()

        # Tier and credit balance
        tier_config = TIERS.get(selected_ws.tier, TIERS["free"])
        balance = queries.get_credit_balance(selected_ws.id)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Credits", balance)
        with col2:
            st.metric("Plan", tier_config["name"])

        # Upgrade prompt for free tier
        if selected_ws.tier == "free":
            st.caption("Upgrade to Pro for more credits and features.")

        # Active project indicator
        project_id = get_current_project_id()
        if project_id:
            project = queries.get_project_by_id(project_id, selected_ws.id)
            if project:
                st.divider()
                st.caption(f"Active project: **{project.name}**")

        st.divider()
