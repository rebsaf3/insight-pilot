"""InsightPilot — Main application entrypoint.
Run with: streamlit run app.py
"""

import streamlit as st

from config.settings import APP_TITLE, STORAGE_DIR, UPLOADS_DIR, LOGOS_DIR, EXPORTS_DIR
from db.database import init_db
from auth.session import get_current_user, logout


def _ensure_directories() -> None:
    """Create required storage directories if they don't exist."""
    for d in (STORAGE_DIR, UPLOADS_DIR, LOGOS_DIR, EXPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def main():
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=":material/analytics:",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Ensure storage directories exist
    _ensure_directories()

    # Initialize database on first run
    init_db()

    # Ensure superadmin is set from ADMIN_EMAIL env var
    from services.admin_service import ensure_superadmin
    ensure_superadmin()

    user = get_current_user()

    if user is None:
        # Unauthenticated — only show login
        login_page = st.Page("pages/login.py", title="Sign In", icon=":material/login:")
        nav = st.navigation([login_page], position="hidden")
    else:
        # Authenticated — render sidebar
        from components.sidebar import render_sidebar
        render_sidebar(user)

        def handle_logout():
            logout()
            st.rerun()

        nav_groups = {
            "Workspace": [
                st.Page("pages/projects.py", title="Projects", icon=":material/folder:", default=True),
                st.Page("pages/upload.py", title="Upload Data", icon=":material/upload:"),
                st.Page("pages/analyze.py", title="Analyze", icon=":material/analytics:"),
            ],
            "Dashboards": [
                st.Page("pages/dashboard_view.py", title="View Dashboard", icon=":material/dashboard:"),
                st.Page("pages/dashboard_edit.py", title="Edit Dashboard", icon=":material/edit:"),
            ],
            "Settings": [
                st.Page("pages/billing.py", title="Billing", icon=":material/payments:"),
                st.Page("pages/branding.py", title="Branding", icon=":material/palette:"),
                st.Page("pages/workspace_settings.py", title="Workspace", icon=":material/group:"),
                st.Page("pages/api_settings.py", title="API", icon=":material/api:"),
                st.Page("pages/settings.py", title="Account", icon=":material/settings:"),
                st.Page(handle_logout, title="Sign Out", icon=":material/logout:"),
            ],
        }

        # Admin pages — only visible to superadmins
        if getattr(user, "is_superadmin", False):
            nav_groups["Admin"] = [
                st.Page("pages/admin/dashboard.py", title="Overview", icon=":material/admin_panel_settings:"),
                st.Page("pages/admin/users.py", title="Users", icon=":material/people:"),
                st.Page("pages/admin/workspaces.py", title="Workspaces", icon=":material/workspaces:"),
                st.Page("pages/admin/billing.py", title="Billing", icon=":material/receipt_long:"),
                st.Page("pages/admin/settings.py", title="System Config", icon=":material/tune:"),
                st.Page("pages/admin/audit.py", title="Audit Log", icon=":material/history:"),
                st.Page("pages/admin/moderation.py", title="Moderation", icon=":material/shield:"),
            ]

        nav = st.navigation(nav_groups)

    nav.run()


if __name__ == "__main__":
    main()
