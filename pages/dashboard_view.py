"""Dashboard view page — render saved dashboards as a grid of charts."""

import streamlit as st
import plotly.io as pio

from auth.session import require_permission, get_current_project_id
from services import credit_service
from db import queries


def show():
    user, ws = require_permission("view_dashboards")

    # Get dashboard to view
    dashboard_id = st.session_state.get("view_dashboard_id")

    if not dashboard_id:
        # Show dashboard list
        _show_dashboard_list(ws)
        return

    dashboard = queries.get_dashboard_by_id(dashboard_id)
    if not dashboard:
        st.error("Dashboard not found.")
        st.session_state.pop("view_dashboard_id", None)
        return

    st.title(dashboard.name)
    if dashboard.description:
        st.caption(dashboard.description)

    # Action bar
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("Back to List"):
            st.session_state.pop("view_dashboard_id", None)
            st.rerun()
    with col2:
        can_export, _ = credit_service.check_export_allowed(ws.id)
        if can_export:
            if st.button("Export PDF"):
                _export_dashboard(dashboard)
        else:
            st.button("Export PDF", disabled=True, help="Upgrade to Pro for exports")

    # Get charts
    charts = queries.get_charts_for_dashboard(dashboard_id)
    if not charts:
        st.info("This dashboard has no charts yet. Go to Analyze to create some.")
        return

    # Render charts in a 2-column grid
    for i in range(0, len(charts), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(charts):
                break
            chart = charts[idx]
            with col:
                st.markdown(f"**{chart.title}**")
                if chart.plotly_json:
                    try:
                        fig = pio.from_json(chart.plotly_json)
                        st.plotly_chart(fig, use_container_width=True, key=f"chart_{chart.id}")
                    except Exception as e:
                        st.error(f"Error rendering chart: {e}")
                else:
                    st.warning("Chart data not available.")
                st.caption(f"Prompt: {chart.user_prompt[:100]}...")


def _show_dashboard_list(ws):
    """Show all dashboards across all projects in the workspace."""
    st.title("Dashboards")

    projects = queries.get_projects_for_workspace(ws.id)
    if not projects:
        st.info("No projects yet. Create a project and generate charts to see dashboards here.")
        return

    any_dashboards = False
    for project in projects:
        dashboards = queries.get_dashboards_for_project(project.id)
        if dashboards:
            any_dashboards = True
            st.subheader(project.name)
            for dash in dashboards:
                chart_count = len(queries.get_charts_for_dashboard(dash.id))
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(f"**{dash.name}** — {chart_count} charts", key=f"dash_{dash.id}", use_container_width=True):
                        st.session_state["view_dashboard_id"] = dash.id
                        st.rerun()
                with col2:
                    st.caption(dash.created_at[:10])

    if not any_dashboards:
        st.info("No dashboards yet. Go to Analyze to create charts and save them to dashboards.")


def _export_dashboard(dashboard):
    """Export dashboard as PDF."""
    try:
        from services.export_service import export_dashboard_as_pdf
        charts = queries.get_charts_for_dashboard(dashboard.id)
        pdf_bytes = export_dashboard_as_pdf(dashboard, charts)
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=f"{dashboard.name}.pdf",
            mime="application/pdf",
        )
    except Exception as e:
        st.error(f"Export failed: {e}")


show()
