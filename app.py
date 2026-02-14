"""InsightPilot — Main application entrypoint.
Run with: streamlit run app.py
"""

import streamlit as st

from config.settings import APP_TITLE
from db.database import init_db
from auth.session import get_current_user, logout


def main():
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=":material/analytics:",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize database on first run
    init_db()

    user = get_current_user()

    if user is None:
        # Unauthenticated — only show login
        login_page = st.Page("pages/login.py", title="Sign In", icon=":material/login:")
        nav = st.navigation([login_page], position="hidden")
    else:
        # Authenticated — full navigation
        def handle_logout():
            logout()
            st.rerun()

        nav = st.navigation(
            {
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
        )

    nav.run()


if __name__ == "__main__":
    main()
