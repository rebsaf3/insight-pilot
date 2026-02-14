"""Common sidebar component — workspace selector, user info, credit display.

NOTE: Streamlit's ``st.navigation()`` always renders the navigation links at
the **top** of the sidebar. Content from ``render_sidebar()`` appears below
the nav links. We design accordingly: nav links → workspace/credits → user.
"""

import streamlit as st

from auth.session import get_current_workspace, set_current_workspace, get_current_project_id
from config.settings import TIERS
from db import queries
from db.models import User
from services.workspace_service import (
    get_user_workspaces,
    check_trial_status,
    get_trial_days_remaining,
)


def render_sidebar(user: User) -> None:
    """Render the common sidebar with workspace selector and user info.

    Called from ``app.py`` before ``st.navigation()``. The actual nav links
    will be injected above this content automatically by Streamlit.
    """
    with st.sidebar:
        # ----- Workspace selector -----
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
            label_visibility="collapsed",
        )

        selected_ws = workspaces[ws_names.index(selected_name)]
        if not current_ws or selected_ws.id != current_ws.id:
            set_current_workspace(selected_ws.id)
            st.rerun()

        # ----- Trial banner -----
        _render_trial_banner(selected_ws)

        # ----- Tier and credit balance -----
        tier_config = TIERS.get(selected_ws.tier, TIERS["free"])
        balance = queries.get_credit_balance(selected_ws.id)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Credits", balance)
        with col2:
            st.metric("Plan", tier_config["name"])

        # Upgrade prompt for free tier (only if not on active trial)
        trial_status = check_trial_status(selected_ws.id)
        if selected_ws.tier == "free" and trial_status != "active":
            st.markdown(
                "<div style='background:#F0FDFA;border:1px solid #CCFBF1;border-radius:8px;"
                "padding:8px 12px;margin-top:4px;font-size:0.78rem;color:#0F766E;"
                "font-family:Inter,sans-serif'>"
                "&#x2728; Upgrade to <b>Pro</b> for more credits and features."
                "</div>",
                unsafe_allow_html=True,
            )

        # ----- Active project indicator -----
        project_id = get_current_project_id()
        if project_id:
            project = queries.get_project_by_id(project_id, selected_ws.id)
            if project:
                st.markdown(
                    f"<div style='margin-top:12px;padding:8px 12px;background:#FFFFFF;"
                    f"border:1px solid #E7E5E4;border-radius:8px;font-family:Inter,sans-serif'>"
                    f"<div style='font-size:0.68rem;color:#57534E;text-transform:uppercase;"
                    f"letter-spacing:0.06em;font-weight:500'>Active Project</div>"
                    f"<div style='font-weight:600;color:#1C1917;font-size:0.85rem;"
                    f"margin-top:2px'>{project.name}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.divider()

        # ----- User identity (bottom of sidebar) -----
        st.markdown(
            f"<div style='font-family:Inter,sans-serif'>"
            f"<div style='font-weight:600;font-size:0.85rem;color:#1C1917'>"
            f"{user.display_name}</div>"
            f"<div style='color:#A8A29E;font-size:0.75rem'>{user.email}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_trial_banner(workspace) -> None:
    """Show a trial status banner if applicable."""
    trial_status = check_trial_status(workspace.id)

    if trial_status == "active":
        days = get_trial_days_remaining(workspace.id)
        day_word = "day" if days == 1 else "days"
        st.markdown(
            f"<div class='ip-trial-banner'>"
            f"<div class='label'>&#x1F680; Pro Trial</div>"
            f"<div class='days'>{days} {day_word} remaining</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    elif trial_status == "expired" and workspace.tier == "free":
        st.markdown(
            "<div style='background:#FEF2F2;border:1px solid #FECACA;border-radius:10px;"
            "padding:10px 14px;margin-bottom:12px;font-family:Inter,sans-serif'>"
            "<div style='font-size:0.7rem;font-weight:600;text-transform:uppercase;"
            "letter-spacing:0.06em;color:#DC2626;margin-bottom:2px'>Trial Ended</div>"
            "<div style='font-size:0.82rem;color:#1C1917;font-weight:500'>"
            "Upgrade to keep Pro features</div>"
            "</div>",
            unsafe_allow_html=True,
        )
