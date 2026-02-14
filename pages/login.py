"""Login and registration page."""

import streamlit as st

from auth.authenticator import authenticate, register_user
from auth.session import create_user_session, get_current_user
from services.workspace_service import create_personal_workspace
from config.settings import APP_TITLE, GOOGLE_CLIENT_ID, MICROSOFT_CLIENT_ID, BASE_URL


def show():
    if get_current_user():
        st.switch_page("pages/projects.py")
        return

    st.markdown(
        f"<h1 style='text-align:center; margin-bottom:0'>{APP_TITLE}</h1>"
        "<p style='text-align:center; color:#666; margin-top:0'>AI-powered data analytics</p>",
        unsafe_allow_html=True,
    )

    # SSO buttons (shown if global SSO credentials are configured)
    _show_sso_buttons()

    tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

    # ----- Login Tab -----
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@company.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
                return

            success, user, error = authenticate(email, password)
            if not success:
                st.error(error)
                return

            # Check if 2FA is required
            if user.has_2fa:
                st.session_state["pending_2fa_user_id"] = user.id
                st.rerun()
                return

            # No 2FA — create session directly
            create_user_session(user)
            st.success("Welcome back!")
            st.rerun()

    # ----- 2FA verification (shown if pending) -----
    if "pending_2fa_user_id" in st.session_state:
        _show_2fa_form()
        return

    # ----- Register Tab -----
    with tab_register:
        with st.form("register_form"):
            reg_name = st.text_input("Display Name", placeholder="Jane Doe")
            reg_email = st.text_input("Email", placeholder="you@company.com", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_password",
                                          help="Minimum 8 characters")
            reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
            reg_submitted = st.form_submit_button("Create Account", use_container_width=True)

        if reg_submitted:
            if not reg_name or not reg_email or not reg_password:
                st.error("All fields are required.")
                return
            if reg_password != reg_confirm:
                st.error("Passwords do not match.")
                return

            success, result = register_user(reg_email, reg_password, reg_name)
            if not success:
                st.error(result)
                return

            user_id = result
            # Create personal workspace
            create_personal_workspace(user_id, reg_name)

            # Auto-login
            from db.queries import get_user_by_id
            user = get_user_by_id(user_id)
            create_user_session(user)
            st.success("Account created! Welcome to InsightPilot.")
            st.rerun()


def _show_2fa_form():
    """Show 2FA verification form."""
    st.subheader("Two-Factor Authentication")

    tab_totp, tab_email, tab_backup = st.tabs(["Authenticator App", "Email Code", "Backup Code"])

    with tab_totp:
        with st.form("totp_form"):
            code = st.text_input("Enter 6-digit code from your authenticator app", max_chars=6)
            submitted = st.form_submit_button("Verify", use_container_width=True)
        if submitted and code:
            from services.tfa_service import verify_totp
            user_id = st.session_state["pending_2fa_user_id"]
            if verify_totp(user_id, code):
                _complete_2fa_login(user_id)
            else:
                st.error("Invalid code. Please try again.")

    with tab_email:
        col1, col2 = st.columns([2, 1])
        with col2:
            if st.button("Send Code", use_container_width=True):
                from services.tfa_service import send_email_2fa_code
                user_id = st.session_state["pending_2fa_user_id"]
                success, msg = send_email_2fa_code(user_id)
                if success:
                    st.success("Code sent to your email.")
                else:
                    st.error(msg)
        with col1:
            with st.form("email_2fa_form"):
                email_code = st.text_input("Enter code from your email", max_chars=6)
                submitted = st.form_submit_button("Verify", use_container_width=True)
            if submitted and email_code:
                from services.tfa_service import verify_email_2fa_code
                user_id = st.session_state["pending_2fa_user_id"]
                if verify_email_2fa_code(user_id, email_code):
                    _complete_2fa_login(user_id)
                else:
                    st.error("Invalid or expired code.")

    with tab_backup:
        with st.form("backup_code_form"):
            backup_code = st.text_input("Enter a backup code")
            submitted = st.form_submit_button("Verify", use_container_width=True)
        if submitted and backup_code:
            from services.tfa_service import verify_backup_code
            user_id = st.session_state["pending_2fa_user_id"]
            if verify_backup_code(user_id, backup_code):
                _complete_2fa_login(user_id)
            else:
                st.error("Invalid or already-used backup code.")

    if st.button("Back to login"):
        st.session_state.pop("pending_2fa_user_id", None)
        st.rerun()


def _complete_2fa_login(user_id: str):
    """Complete login after successful 2FA verification."""
    from db.queries import get_user_by_id
    user = get_user_by_id(user_id)
    create_user_session(user)
    st.session_state.pop("pending_2fa_user_id", None)
    st.success("Welcome back!")
    st.rerun()


def _show_sso_buttons():
    """Show SSO login buttons if credentials are configured."""
    has_google = bool(GOOGLE_CLIENT_ID)
    has_microsoft = bool(MICROSOFT_CLIENT_ID)

    if not has_google and not has_microsoft:
        return

    cols = st.columns(2)
    if has_google:
        with cols[0]:
            from services.sso_service import get_google_auth_url
            url = get_google_auth_url("")
            st.link_button("Sign in with Google", url, use_container_width=True)
    if has_microsoft:
        with cols[1]:
            from services.sso_service import get_microsoft_auth_url
            url = get_microsoft_auth_url("")
            st.link_button("Sign in with Microsoft", url, use_container_width=True)

    st.divider()


show()
