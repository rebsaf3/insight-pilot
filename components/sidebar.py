"""Common sidebar component — workspace selector, user info, credit display."""

import streamlit as st

from auth.session import get_current_workspace, set_current_workspace
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

        # Credit balance
        balance = queries.get_credit_balance(selected_ws.id)
        tier = selected_ws.tier.capitalize()
        st.metric(f"Credits ({tier})", balance)

        st.divider()
