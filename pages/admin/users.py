"""Admin — User Management page."""

import streamlit as st

from auth.session import require_superadmin
from db import queries
from services.admin_service import toggle_superadmin


def show():
    admin = require_superadmin()

    st.title("User Management")
    st.caption("View and manage all users across the platform")

    # Pagination
    page = st.session_state.get("admin_users_page", 0)
    per_page = 25
    total = queries.count_all_users()

    users = queries.get_all_users(limit=per_page, offset=page * per_page)

    if not users:
        st.info("No users found.")
        return

    st.caption(f"Showing {page * per_page + 1}-{min((page + 1) * per_page, total)} of {total} users")

    for user in users:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            with col1:
                st.markdown(f"**{user.display_name or user.email}**")
                st.caption(user.email)
            with col2:
                # Show workspaces this user belongs to
                workspaces = queries.get_workspaces_for_user(user.id)
                ws_names = ", ".join(w.name for w in workspaces[:3])
                if len(workspaces) > 3:
                    ws_names += f" +{len(workspaces) - 3} more"
                st.caption(f"Workspaces: {ws_names or 'None'}")
            with col3:
                if user.is_superadmin:
                    st.success("Admin")
                else:
                    st.caption("User")
            with col4:
                if user.id != admin.id:  # Can't demote yourself
                    new_status = not user.is_superadmin
                    label = "Revoke Admin" if user.is_superadmin else "Make Admin"
                    if st.button(label, key=f"admin_{user.id}"):
                        toggle_superadmin(user.id, new_status, admin.id)
                        st.rerun()

            # Expandable details
            with st.expander("Details", expanded=False):
                dc1, dc2, dc3 = st.columns(3)
                dc1.metric("2FA", "Enabled" if user.has_2fa else "Disabled")
                dc2.metric("SSO", user.sso_provider or "None")
                dc3.metric("Joined", user.created_at[:10] if user.created_at else "Unknown")

                if workspaces:
                    st.markdown("**Workspaces:**")
                    for w in workspaces:
                        role = queries.get_member_role(w.id, user.id) or "unknown"
                        balance = queries.get_credit_balance(w.id)
                        st.caption(f"• {w.name} — {role} — {w.tier} tier — {balance} credits")

    # Pagination controls
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    max_page = max(0, (total - 1) // per_page)
    with col_prev:
        if st.button("Previous", disabled=page <= 0):
            st.session_state["admin_users_page"] = page - 1
            st.rerun()
    with col_info:
        st.caption(f"Page {page + 1} of {max_page + 1}")
    with col_next:
        if st.button("Next", disabled=page >= max_page):
            st.session_state["admin_users_page"] = page + 1
            st.rerun()


show()
