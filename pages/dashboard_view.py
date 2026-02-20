"""Dashboard view page — render saved dashboards as a grid of charts."""

import io
import zipfile
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
    st.info("📊 View and interact with your dashboards here. Dashboards display your charts and insights in a single place for easy sharing and review.")
    if dashboard.description:
        st.caption(dashboard.description)

    style = dashboard.style_config or {}
    grid_columns = int(style.get("columns", 2))
    grid_columns = min(max(grid_columns, 1), 3)
    compact_mode = bool(style.get("compact_mode", False))
    show_prompt = bool(style.get("show_prompt", True))

    # Action bar
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 3])
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
    with col3:
        can_export, _ = credit_service.check_export_allowed(ws.id)
        if can_export:
            if st.button("Export Excel"):
                _export_dashboard_excel(dashboard)
        else:
            st.button("Export Excel", disabled=True, help="Upgrade to Pro for exports")
    with col4:
        can_export, _ = credit_service.check_export_allowed(ws.id)
        if can_export:
            if st.button("Export PNG Zip"):
                _export_dashboard_png_zip(dashboard)
        else:
            st.button("Export PNG Zip", disabled=True, help="Upgrade to Pro for exports")
    with col5:
        if st.button("Scheduled Reports"):
            st.switch_page("pages/scheduled_reports.py")

    # Get charts
    charts = queries.get_charts_for_dashboard(dashboard_id)
    if not charts:
        st.info("This dashboard has no charts yet. Go to Analyze to create some.")
        return

    # Render charts in configured grid
    for i in range(0, len(charts), grid_columns):
        cols = st.columns(grid_columns)
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
                if show_prompt:
                    prompt_preview = chart.user_prompt[:80] if compact_mode else chart.user_prompt[:130]
                    suffix = "..." if len(chart.user_prompt) > len(prompt_preview) else ""
                    st.caption(f"Prompt: {prompt_preview}{suffix}")


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


def _export_dashboard_excel(dashboard):
    try:
        from services.export_service import export_dashboard_as_excel
        charts = queries.get_charts_for_dashboard(dashboard.id)
        xlsx_bytes = export_dashboard_as_excel(dashboard, charts)
        st.download_button(
            "Download Excel",
            data=xlsx_bytes,
            file_name=f"{dashboard.name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        st.error(f"Export failed: {e}")


def _export_dashboard_png_zip(dashboard):
    try:
        from services.export_service import export_dashboard_as_images
        charts = queries.get_charts_for_dashboard(dashboard.id)
        images = export_dashboard_as_images(dashboard, charts)
        if not images:
            st.warning("No chart images available for export.")
            return
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for title, png in images:
                safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in title)[:60]
                filename = f"{safe or 'chart'}.png"
                zf.writestr(filename, png)
        st.download_button(
            "Download PNG Zip",
            data=buf.getvalue(),
            file_name=f"{dashboard.name}-charts.zip",
            mime="application/zip",
        )
    except Exception as e:
        st.error(f"Export failed: {e}")


show()
