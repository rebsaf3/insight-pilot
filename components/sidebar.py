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
        # User identity
        st.markdown(
            f"<div style='margin-bottom:4px'>"
            f"<span style='font-weight:600;font-size:0.95rem;color:#111827'>{user.display_name}</span>"
            f"</div>"
            f"<div style='color:#6B7280;font-size:0.8rem;margin-bottom:12px'>{user.email}</div>",
            unsafe_allow_html=True,
        )

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
            st.markdown(
                "<div style='background:#EEF0FC;border:1px solid #D4D9F7;border-radius:6px;"
                "padding:8px 12px;margin-top:8px;font-size:0.8rem;color:#2D3FE0'>"
                "Upgrade to Pro for more credits and features."
                "</div>",
                unsafe_allow_html=True,
            )

        # Active project indicator
        project_id = get_current_project_id()
        if project_id:
            project = queries.get_project_by_id(project_id, selected_ws.id)
            if project:
                st.divider()
                st.markdown(
                    f"<div style='font-size:0.8rem;color:#6B7280'>Active project</div>"
                    f"<div style='font-weight:600;color:#111827;font-size:0.9rem'>{project.name}</div>",
                    unsafe_allow_html=True,
                )

        st.divider()
