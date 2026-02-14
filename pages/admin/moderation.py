"""Admin — Content Moderation page."""

import streamlit as st

from auth.session import require_superadmin
from db import queries


def show():
    require_superadmin()

    st.title("Content Moderation")
    st.caption("Review prompts sent to Claude AI across all workspaces")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        search_query = st.text_input("Search prompts", placeholder="Type to search...", key="mod_search")
    with col2:
        errors_only = st.checkbox("Show errors only", key="mod_errors_only")

    # Pagination
    page = st.session_state.get("mod_page", 0)
    per_page = 25

    entries = queries.get_all_prompt_history(limit=per_page, offset=page * per_page)

    if search_query:
        entries = [e for e in entries if search_query.lower() in (e.prompt_text or "").lower()]

    if errors_only:
        entries = [e for e in entries if e.response_error]

    if not entries:
        st.info("No prompt history entries found.")
        return

    st.caption(f"Showing page {page + 1}")

    for entry in entries:
        user = queries.get_user_by_id(entry.user_id)
        ws = queries.get_workspace_by_id(entry.workspace_id)

        has_error = bool(entry.response_error)
        border_color = "red" if has_error else None

        with st.container(border=True):
            # Header row
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            with col1:
                st.caption(f"**User:** {user.email if user else entry.user_id}")
            with col2:
                st.caption(f"**Workspace:** {ws.name if ws else entry.workspace_id[:12]}")
            with col3:
                st.caption(f"**Tokens:** {entry.tokens_used:,}")
            with col4:
                st.caption(entry.created_at[:16] if entry.created_at else "")

            # Prompt text
            st.markdown(f"**Prompt:** {entry.prompt_text[:200]}{'...' if len(entry.prompt_text) > 200 else ''}")

            # Error indicator
            if has_error:
                st.error(f"Error: {entry.response_error[:150]}")

            # Expandable details
            with st.expander("Full Details"):
                st.markdown("**Full Prompt:**")
                st.text(entry.prompt_text)

                if entry.response_code:
                    st.markdown("**Generated Code:**")
                    st.code(entry.response_code, language="python")

                if entry.response_error:
                    st.markdown("**Error:**")
                    st.error(entry.response_error)

                st.caption(f"Model: {entry.model_used} | Project: {entry.project_id[:12]}...")

    # Pagination
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("Previous", disabled=page <= 0, key="mod_prev"):
            st.session_state["mod_page"] = page - 1
            st.rerun()
    with col_info:
        st.caption(f"Page {page + 1}")
    with col_next:
        if st.button("Next", disabled=len(entries) < per_page, key="mod_next"):
            st.session_state["mod_page"] = page + 1
            st.rerun()


show()
