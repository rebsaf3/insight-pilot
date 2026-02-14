"""Admin — Audit Log viewer page."""

import streamlit as st

from auth.session import require_superadmin
from db import queries


def show():
    require_superadmin()

    st.title("Audit Log")
    st.caption("View all administrative actions and system events")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        entity_filter = st.selectbox(
            "Filter by Entity Type",
            ["All", "user", "workspace", "system"],
            key="audit_entity_filter",
        )
    with col2:
        user_filter = st.text_input("Filter by User ID", key="audit_user_filter", placeholder="Leave empty for all")

    # Pagination
    page = st.session_state.get("audit_page", 0)
    per_page = 30

    kwargs = {"limit": per_page, "offset": page * per_page}
    if entity_filter != "All":
        kwargs["entity_type"] = entity_filter
    if user_filter:
        kwargs["user_id"] = user_filter

    entries = queries.get_audit_log(**kwargs)

    if not entries:
        st.info("No audit log entries found matching the filters.")
        return

    for entry in entries:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 2, 3, 1])
            with col1:
                st.markdown(f"**{entry.action}**")
                st.caption(f"{entry.entity_type}")
            with col2:
                if entry.user_id:
                    user = queries.get_user_by_id(entry.user_id)
                    st.caption(user.email if user else entry.user_id)
                else:
                    st.caption("System")
            with col3:
                if entry.details:
                    if isinstance(entry.details, dict):
                        details_str = ", ".join(f"{k}: {v}" for k, v in entry.details.items())
                    else:
                        details_str = str(entry.details)
                    st.caption(details_str[:100])
                if entry.entity_id:
                    st.caption(f"Entity: {entry.entity_id[:12]}...")
            with col4:
                st.caption(entry.created_at[:16] if entry.created_at else "")

    # Pagination
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("Previous", disabled=page <= 0, key="audit_prev"):
            st.session_state["audit_page"] = page - 1
            st.rerun()
    with col_info:
        st.caption(f"Page {page + 1}")
    with col_next:
        if st.button("Next", disabled=len(entries) < per_page, key="audit_next"):
            st.session_state["audit_page"] = page + 1
            st.rerun()


show()
