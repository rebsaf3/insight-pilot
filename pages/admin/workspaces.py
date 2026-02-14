"""Admin — Workspace Management page."""

import streamlit as st

from auth.session import require_superadmin
from config.settings import TIERS
from db import queries
from services.admin_service import adjust_workspace_credits, change_workspace_tier


def show():
    admin = require_superadmin()

    st.title("Workspace Management")
    st.caption("View and manage all workspaces across the platform")

    # Pagination
    page = st.session_state.get("admin_ws_page", 0)
    per_page = 20
    total = queries.count_all_workspaces()

    workspaces = queries.get_all_workspaces(limit=per_page, offset=page * per_page)

    if not workspaces:
        st.info("No workspaces found.")
        return

    st.caption(f"Showing {page * per_page + 1}-{min((page + 1) * per_page, total)} of {total} workspaces")

    for ws in workspaces:
        owner = queries.get_user_by_id(ws.owner_id)
        member_count = queries.count_workspace_members(ws.id)
        balance = queries.get_credit_balance(ws.id)

        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
            with col1:
                st.markdown(f"**{ws.name}**")
                st.caption(f"Owner: {owner.email if owner else 'Unknown'}")
            with col2:
                st.metric("Tier", ws.tier.capitalize())
            with col3:
                st.metric("Members", member_count)
            with col4:
                st.metric("Credits", balance)
            with col5:
                st.caption(f"Created: {ws.created_at[:10]}")

            # Admin actions
            with st.expander("Admin Actions", expanded=False):
                act_col1, act_col2 = st.columns(2)

                with act_col1:
                    # Change tier
                    tier_options = list(TIERS.keys())
                    current_idx = tier_options.index(ws.tier) if ws.tier in tier_options else 0
                    new_tier = st.selectbox(
                        "Change Tier",
                        tier_options,
                        index=current_idx,
                        format_func=lambda t: TIERS[t]["name"],
                        key=f"tier_{ws.id}",
                    )
                    if new_tier != ws.tier:
                        if st.button("Apply Tier Change", key=f"apply_tier_{ws.id}"):
                            change_workspace_tier(ws.id, new_tier, admin.id)
                            st.success(f"Tier changed to {TIERS[new_tier]['name']}")
                            st.rerun()

                with act_col2:
                    # Adjust credits
                    amount = st.number_input(
                        "Credit Adjustment",
                        min_value=-10000, max_value=10000, value=0, step=50,
                        help="Positive to add, negative to deduct",
                        key=f"credits_{ws.id}",
                    )
                    reason = st.text_input("Reason", key=f"reason_{ws.id}", placeholder="Manual adjustment")
                    if amount != 0 and reason:
                        if st.button("Apply Credit Adjustment", key=f"apply_credits_{ws.id}"):
                            new_balance = adjust_workspace_credits(ws.id, admin.id, amount, reason)
                            st.success(f"Credits adjusted. New balance: {new_balance}")
                            st.rerun()

                # Members list
                members = queries.get_workspace_members(ws.id)
                if members:
                    st.markdown("**Members:**")
                    for m in members:
                        u = queries.get_user_by_id(m.user_id)
                        st.caption(f"• {u.email if u else m.user_id} — {m.role}")

    # Pagination controls
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    max_page = max(0, (total - 1) // per_page)
    with col_prev:
        if st.button("Previous", disabled=page <= 0, key="ws_prev"):
            st.session_state["admin_ws_page"] = page - 1
            st.rerun()
    with col_info:
        st.caption(f"Page {page + 1} of {max_page + 1}")
    with col_next:
        if st.button("Next", disabled=page >= max_page, key="ws_next"):
            st.session_state["admin_ws_page"] = page + 1
            st.rerun()


show()
