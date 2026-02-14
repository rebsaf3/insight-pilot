"""InsightPilot — Main application entrypoint.
Run with: streamlit run app.py
"""

import streamlit as st

from config.settings import APP_TITLE, STORAGE_DIR, UPLOADS_DIR, LOGOS_DIR, EXPORTS_DIR
from db.database import init_db
from auth.session import get_current_user, logout, get_current_workspace


def _ensure_directories() -> None:
    """Create required storage directories if they don't exist."""
    for d in (STORAGE_DIR, UPLOADS_DIR, LOGOS_DIR, EXPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _get_user_theme(user) -> str:
    """Return the user's preferred theme ('light' or 'dark').

    Wrapped in try/except so a DB or model error never blocks navigation.
    """
    if user is None:
        return "light"
    try:
        from db.queries import get_user_preferences
        prefs = get_user_preferences(user.id)
        return prefs.theme if prefs else "light"
    except Exception:
        return "light"


def _check_trial_expiry() -> None:
    """Auto-downgrade workspaces whose trial has expired.

    Wrapped in try/except so a failure never blocks navigation.
    """
    try:
        ws = get_current_workspace()
        if ws is None:
            return
        from services.workspace_service import check_trial_status, expire_trial
        if check_trial_status(ws.id) == "expired" and ws.tier != "free":
            expire_trial(ws.id)
    except Exception:
        pass


def main():
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inject custom CSS theme early (import only — called after user is resolved)
    from components.theme import inject_custom_css

    # Ensure storage directories exist
    _ensure_directories()

    # Initialize database on first run
    init_db()

    # Ensure superadmin is set from ADMIN_EMAIL env var
    from services.admin_service import ensure_superadmin
    ensure_superadmin()

    user = get_current_user()

    # Inject CSS — pass user theme preference (guarded against errors)
    theme = _get_user_theme(user)
    inject_custom_css(theme=theme)

    # Auto-downgrade expired trials (guarded — never blocks navigation)
    if user:
        _check_trial_expiry()

    if user is None:
        # Unauthenticated — only show login
        login_page = st.Page("pages/login.py", title="Sign In", icon=":material/login:")
        nav = st.navigation([login_page], position="hidden")
    else:
        # Authenticated — render sidebar (guarded so nav always runs)
        try:
            from components.sidebar import render_sidebar
            render_sidebar(user)
        except Exception:
            pass  # sidebar rendering failure must not block navigation

        def handle_logout():
            logout()
            st.rerun()

        nav_groups = {
            "Workspace": [
                st.Page("pages/projects.py", title="Projects", icon=":material/folder:", default=True),
                st.Page("pages/upload.py", title="Upload Data", icon=":material/upload:"),
                st.Page("pages/analyze.py", title="Analyze", icon=":material/analytics:"),
                st.Page("pages/usage.py", title="Usage", icon=":material/bar_chart:"),
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
