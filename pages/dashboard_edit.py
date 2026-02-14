"""Dashboard edit page — reorder charts, delete charts, rename dashboard."""

import streamlit as st

from auth.session import require_permission
from db import queries


def show():
    user, ws = require_permission("create_edit_dashboards")

    st.title("Edit Dashboard")

    dashboard_id = st.session_state.get("view_dashboard_id")
    if not dashboard_id:
        st.warning("Select a dashboard to edit from the View Dashboard page.")
        st.stop()

    dashboard = queries.get_dashboard_by_id(dashboard_id)
    if not dashboard:
        st.error("Dashboard not found.")
        st.stop()

    # Dashboard details
    with st.form("edit_dashboard"):
        new_name = st.text_input("Dashboard Name", value=dashboard.name)
        new_desc = st.text_area("Description", value=dashboard.description)
        if st.form_submit_button("Update"):
            queries.update_dashboard(dashboard_id, name=new_name, description=new_desc)
            st.success("Dashboard updated!")
            st.rerun()

    st.divider()

    # Charts management
    st.subheader("Charts")
    charts = queries.get_charts_for_dashboard(dashboard_id)

    if not charts:
        st.info("No charts in this dashboard.")
        return

    for i, chart in enumerate(charts):
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            st.markdown(f"**{i + 1}. {chart.title}**")
            st.caption(chart.user_prompt[:80])
        with col2:
            # Move up/down
            if i > 0 and st.button("Up", key=f"up_{chart.id}"):
                order = [c.id for c in charts]
                order[i], order[i - 1] = order[i - 1], order[i]
                queries.reorder_charts(dashboard_id, order)
                st.rerun()
        with col3:
            if st.button("Delete", key=f"del_{chart.id}", type="secondary"):
                queries.delete_chart(chart.id)
                st.rerun()

    st.divider()

    # Danger zone
    with st.expander("Danger Zone", expanded=False):
        st.warning("This action cannot be undone.")
        if st.button("Delete Dashboard", type="secondary"):
            queries.delete_dashboard(dashboard_id)
            st.session_state.pop("view_dashboard_id", None)
            st.success("Dashboard deleted.")
            st.rerun()


show()
