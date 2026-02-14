"""Login and registration page."""

import streamlit as st

from auth.authenticator import authenticate, register_user
from auth.session import create_user_session, get_current_user
from services.workspace_service import create_personal_workspace
from config.settings import APP_TITLE, GOOGLE_CLIENT_ID, MICROSOFT_CLIENT_ID, BASE_URL

# ---------------------------------------------------------------------------
# Page-specific CSS — centered card layout for the login experience
# ---------------------------------------------------------------------------
_LOGIN_CSS = """
<style>
/* --- Center the login content in the viewport ---------------------- */
[data-testid="stMainBlockContainer"] {
    max-width: 480px !important;
    margin: 0 auto !important;
    padding-top: 2rem !important;
}

/* --- Login card wrapper -------------------------------------------- */
.login-card {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 2.5rem 2rem 2rem;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), 0 1px 4px rgba(0, 0, 0, 0.04);
    margin-bottom: 1.5rem;
}

/* --- Brand header -------------------------------------------------- */
.login-brand {
    text-align: center;
    margin-bottom: 2rem;
}

.login-brand h1 {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    font-weight: 800 !important;
    font-size: 2.2rem !important;
    color: #111827 !important;
    letter-spacing: -0.03em;
    margin-bottom: 0.25rem !important;
    line-height: 1.1 !important;
}

.login-brand .logo-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 56px;
    background: linear-gradient(135deg, #2D3FE0 0%, #5B6CF0 100%);
    border-radius: 14px;
    margin-bottom: 1rem;
    box-shadow: 0 4px 12px rgba(45, 63, 224, 0.3);
}

.login-brand .logo-icon svg {
    width: 28px;
    height: 28px;
}

.login-brand p {
    font-family: 'Inter', sans-serif !important;
    color: #6B7280 !important;
    font-size: 1rem !important;
    font-weight: 400 !important;
    margin-top: 0 !important;
}

/* --- Footer text --------------------------------------------------- */
.login-footer {
    text-align: center;
    font-size: 0.8rem;
    color: #9CA3AF;
    margin-top: 1.5rem;
    font-family: 'Inter', sans-serif;
}

.login-footer a {
    color: #2D3FE0;
    text-decoration: none;
}

/* --- Override form styling for login ------------------------------- */
[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
}

/* --- Primary button — make it taller and more prominent ------------ */
button[type="submit"],
button[data-testid="stBaseButton-primary"] {
    background-color: #2D3FE0 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    padding: 0.65rem 1.5rem !important;
    font-size: 0.95rem !important;
    transition: all 0.2s ease !important;
    margin-top: 0.5rem !important;
}

button[type="submit"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
    background-color: #1E2FC0 !important;
    box-shadow: 0 4px 12px rgba(45, 63, 224, 0.3) !important;
    transform: translateY(-1px);
}

/* --- Tab styling --------------------------------------------------- */
button[data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.95rem !important;
    color: #6B7280 !important;
    padding-bottom: 0.75rem !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #2D3FE0 !important;
    font-weight: 600 !important;
}

/* --- Input fields -------------------------------------------------- */
[data-testid="stTextInput"] input {
    border: 1.5px solid #E5E7EB !important;
    border-radius: 8px !important;
    padding: 0.6rem 0.75rem !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
    transition: all 0.2s ease !important;
}

[data-testid="stTextInput"] input:focus {
    border-color: #2D3FE0 !important;
    box-shadow: 0 0 0 3px rgba(45, 63, 224, 0.1) !important;
}

/* --- SSO buttons --------------------------------------------------- */
a[data-testid="stBaseButton-secondary"] {
    border: 1.5px solid #E5E7EB !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    color: #111827 !important;
    transition: all 0.15s ease !important;
}

a[data-testid="stBaseButton-secondary"]:hover {
    border-color: #2D3FE0 !important;
    color: #2D3FE0 !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05) !important;
}

/* --- Hide Streamlit branding on login ------------------------------ */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stHeader"] {
    background: transparent !important;
    height: 0 !important;
    min-height: 0 !important;
    overflow: hidden !important;
    padding: 0 !important;
}
</style>
"""


def show():
    if get_current_user():
        st.switch_page("pages/projects.py")
        return

    # Inject login-specific CSS
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)

    # Brand header with icon
    st.markdown(
        f"""
        <div class="login-brand">
            <div class="logo-icon" style="display:inline-flex;align-items:center;
                justify-content:center;width:56px;height:56px;
                background:linear-gradient(135deg, #2D3FE0 0%, #5B6CF0 100%);
                border-radius:14px;margin-bottom:1rem;
                box-shadow:0 4px 12px rgba(45,63,224,0.3)">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
                     xmlns="http://www.w3.org/2000/svg">
                    <path d="M3 3V21H21" stroke="white" stroke-width="2"
                          stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M7 14L11 10L15 13L21 7" stroke="white" stroke-width="2"
                          stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
            <h1>{APP_TITLE}</h1>
            <p>AI-powered data analytics</p>
        </div>
        """,
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

    # Footer
    st.markdown(
        '<div class="login-footer">Secure, private, and powered by AI</div>',
        unsafe_allow_html=True,
    )


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
