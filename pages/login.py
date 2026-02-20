"""Login and registration page."""

import streamlit as st

from auth.authenticator import authenticate, register_user
from auth.session import create_user_session, get_current_user
from services.workspace_service import create_personal_workspace
from config.settings import GOOGLE_CLIENT_ID, MICROSOFT_CLIENT_ID

# ---------------------------------------------------------------------------
# Page-specific CSS — split-screen marketing + auth panel
# ---------------------------------------------------------------------------
_LOGIN_CSS = """
<style>
/* --- App background ------------------------------------------------ */
[data-testid="stApp"] {
    background: #F2E5D3 !important;
}

[data-testid="stMainBlockContainer"] {
    max-width: 100% !important;
    padding: 0 !important;
}

/* --- Split layout (Streamlit columns) ------------------------------ */
div[data-testid="stMainBlockContainer"] > div > div[data-testid="stHorizontalBlock"] {
    gap: 0 !important;
    align-items: stretch !important;
}

div[data-testid="stMainBlockContainer"] > div > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    padding: 0 !important;
}

div[data-testid="stMainBlockContainer"] > div > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child {
    background: radial-gradient(1200px 600px at 10% 20%, rgba(255,255,255,0.55) 0%, rgba(255,255,255,0) 55%),
                linear-gradient(180deg, #F3E5D0 0%, #EEDCC2 100%);
    min-height: 100vh;
    padding: 76px 80px 56px 80px !important;
}

div[data-testid="stMainBlockContainer"] > div > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
    background: #FAFCFF;
    min-height: 100vh;
    border-left: 1px solid rgba(28, 25, 23, 0.06);
    padding: 76px 64px 56px 64px !important;
    display: flex;
    align-items: center;
}

div[data-testid="stMainBlockContainer"] > div > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) > div {
    width: 100%;
    max-width: 420px;
    margin: 0 auto;
}

@media (max-width: 920px) {
    div[data-testid="stMainBlockContainer"] > div > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child {
        display: none !important;
    }
    div[data-testid="stMainBlockContainer"] > div > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
        border-left: none !important;
        padding: 56px 22px 44px 22px !important;
        min-height: auto;
    }
}

/* --- Left panel ---------------------------------------------------- */
.auth-left-wrap {
    max-width: 700px;
    margin: 0 auto;
}

.auth-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 26px;
}

.auth-brand .logo-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    background: linear-gradient(135deg, #0F766E 0%, #10B981 100%);
    border-radius: 12px;
    box-shadow: 0 6px 18px rgba(15, 118, 110, 0.18);
}

.auth-brand .logo-icon svg {
    width: 22px;
    height: 22px;
}

.auth-brand .brand-name {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
    font-size: 1.1rem !important;
    color: #0B2A29 !important;
}

.auth-hero h1 {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em;
    font-size: 3.25rem !important;
    line-height: 1.05 !important;
    color: #0F172A !important;
    margin: 0 0 18px 0 !important;
}

.auth-hero p {
    font-family: 'Inter', sans-serif !important;
    font-size: 1.05rem !important;
    line-height: 1.6 !important;
    color: rgba(15, 23, 42, 0.72) !important;
    margin: 0 0 30px 0 !important;
    max-width: 52ch;
}

.auth-feature-list {
    margin-top: 12px;
}

.auth-feature {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    margin: 14px 0;
}

.auth-feature .check {
    width: 22px;
    height: 22px;
    border-radius: 999px;
    background: rgba(15, 118, 110, 0.12);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-top: 2px;
    flex: 0 0 auto;
}

.auth-feature .check svg {
    width: 14px;
    height: 14px;
}

.auth-feature .text {
    font-family: 'Inter', sans-serif !important;
    color: rgba(15, 23, 42, 0.74) !important;
    font-size: 0.98rem !important;
    line-height: 1.45 !important;
}

.auth-feature .text b {
    color: rgba(15, 23, 42, 0.92) !important;
    font-weight: 600 !important;
}

/* --- Right panel typography --------------------------------------- */
.auth-right-title h2 {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
    font-size: 2.05rem !important;
    color: #0F172A !important;
    margin: 0 0 6px 0 !important;
}

.auth-right-title p {
    font-family: 'Inter', sans-serif !important;
    color: rgba(15, 23, 42, 0.62) !important;
    margin: 0 0 22px 0 !important;
    font-size: 0.95rem !important;
}

.auth-field-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin: 10px 0 6px 0;
}

.auth-label {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    color: rgba(15, 23, 42, 0.78) !important;
}

.auth-link {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    color: #0F766E !important;
    text-decoration: none !important;
}

.auth-link:hover {
    text-decoration: underline !important;
}

/* --- Override form styling for login ------------------------------- */
[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
    background: transparent !important;
}

/* --- Primary button — teal, warm ----------------------------------- */
button[type="submit"],
button[data-testid="stBaseButton-primary"] {
    background-color: #0F766E !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    padding: 0.72rem 1.5rem !important;
    font-size: 0.95rem !important;
    transition: all 0.2s ease !important;
    margin-top: 0.75rem !important;
}

button[type="submit"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
    background-color: #0D6660 !important;
    box-shadow: 0 4px 12px rgba(15, 118, 110, 0.25) !important;
    transform: translateY(-1px);
}

/* --- Input fields -------------------------------------------------- */
[data-testid="stTextInput"] input {
    border: 1.5px solid #E7E5E4 !important;
    border-radius: 8px !important;
    padding: 0.55rem 0.75rem !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    background: #FFFFFF !important;
    transition: all 0.2s ease !important;
}

[data-testid="stTextInput"] input:focus {
    border-color: #0F766E !important;
    box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.08) !important;
}

/* --- Checkbox alignment ------------------------------------------- */
[data-testid="stCheckbox"] {
    margin-top: 6px;
}

[data-testid="stCheckbox"] label {
    font-family: 'Inter', sans-serif !important;
    color: rgba(15, 23, 42, 0.72) !important;
    font-size: 0.88rem !important;
}

/* --- SSO buttons --------------------------------------------------- */
a[data-testid="stBaseButton-secondary"] {
    border: 1.5px solid #E7E5E4 !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    color: #1C1917 !important;
    transition: all 0.2s ease !important;
}

a[data-testid="stBaseButton-secondary"]:hover {
    border-color: #0F766E !important;
    color: #0F766E !important;
    box-shadow: 0 2px 8px rgba(28, 25, 23, 0.05) !important;
}

/* --- Bottom helper text ------------------------------------------- */
.auth-bottom {
    margin-top: 18px;
    text-align: center;
    font-family: 'Inter', sans-serif !important;
    color: rgba(15, 23, 42, 0.60) !important;
    font-size: 0.9rem !important;
}

/* --- Hide Streamlit branding on login ------------------------------ */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stHeader"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stDecoration"] {
    display: none !important;
}
</style>
"""


def show():
    if get_current_user():
        st.switch_page("pages/projects.py")
        return

    # Inject login-specific CSS
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)

    try:
        view = st.query_params.get("view", "login")
    except Exception:
        params = st.experimental_get_query_params()
        view = params.get("view", ["login"])
    if isinstance(view, list):
        view = view[0] if view else "login"
    if view not in {"login", "register", "forgot"}:
        view = "login"

    left, right = st.columns([1.72, 1.0], gap="large")

    with left:
        st.markdown(
            f"""
            <div class="auth-left-wrap">
                <div class="auth-brand">
                    <div class="logo-icon">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
                             xmlns="http://www.w3.org/2000/svg">
                            <path d="M3 3V21H21" stroke="white" stroke-width="2"
                                  stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M7 14L11 10L15 13L21 7" stroke="white" stroke-width="2"
                                  stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                    <div class="brand-name">NyLi Insights</div>
                </div>

                <div class="auth-hero">
                    <h1>Deploy AI Insights<br/>That Drive Action</h1>
                    <p>
                        NyLi Insights gives your organization a secure analytics workspace
                        with live dashboards, governed AI analysis, and publish-ready reporting.
                    </p>
                </div>

                <div class="auth-feature-list">
                    <div class="auth-feature">
                        <div class="check">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M20 6L9 17L4 12" stroke="#0F766E" stroke-width="2.5"
                                      stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </div>
                        <div class="text"><b>Portfolio intelligence in one place</b> — unify market data, KPI trends, and analyst context across teams.</div>
                    </div>
                    <div class="auth-feature">
                        <div class="check">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M20 6L9 17L4 12" stroke="#0F766E" stroke-width="2.5"
                                      stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </div>
                        <div class="text"><b>Trusted AI analysis</b> — responses stay grounded in your approved datasets, reports, and prompts.</div>
                    </div>
                    <div class="auth-feature">
                        <div class="check">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M20 6L9 17L4 12" stroke="#0F766E" stroke-width="2.5"
                                      stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </div>
                        <div class="text"><b>Audit-ready workflows</b> — capture revisions, assumptions, and exports for compliance and review.</div>
                    </div>
                    <div class="auth-feature">
                        <div class="check">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M20 6L9 17L4 12" stroke="#0F766E" stroke-width="2.5"
                                      stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </div>
                        <div class="text"><b>Executive-ready delivery</b> — publish dashboards and insight briefs to stakeholders in minutes.</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            f"""
            <div class="auth-right-title">
                <h2>{'Welcome Back' if view != 'register' else 'Create Account'}</h2>
                <p>{'Sign in to your NyLi Insights account' if view != 'register' else 'Create your NyLi Insights account'}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ----- 2FA verification (shown if pending) -----
        if "pending_2fa_user_id" in st.session_state:
            _show_2fa_form()
            return

        if view == "forgot":
            st.info("Password resets are handled by your workspace admin. If you need help, contact support.")
            st.markdown('<div class="auth-bottom"><a class="auth-link" href="?view=login">Back to sign in</a></div>', unsafe_allow_html=True)
            return

        if view == "login":
            # SSO buttons (shown if global SSO credentials are configured)
            _show_sso_buttons()

            remembered_email = st.session_state.get("remembered_email", "")
            with st.form("login_form"):
                st.markdown('<div class="auth-field-row"><span class="auth-label">Email</span></div>', unsafe_allow_html=True)
                email = st.text_input(
                    "Email",
                    label_visibility="collapsed",
                    placeholder="you@example.com",
                    value=remembered_email,
                )

                st.markdown(
                    '<div class="auth-field-row"><span class="auth-label">Password</span><a class="auth-link" href="?view=forgot">Forgot password?</a></div>',
                    unsafe_allow_html=True,
                )
                password = st.text_input(
                    "Password",
                    label_visibility="collapsed",
                    type="password",
                    placeholder="Enter your password",
                )

                remember = st.checkbox("Remember my username", value=bool(remembered_email))
                submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("Please enter both email and password.")
                    return

                if remember:
                    st.session_state["remembered_email"] = email
                else:
                    st.session_state.pop("remembered_email", None)

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

            st.markdown(
                '<div class="auth-bottom">Don\'t have an account? <a class="auth-link" href="?view=register">Create one</a></div>',
                unsafe_allow_html=True,
            )

        if view == "register":
            with st.form("register_form"):
                st.markdown('<div class="auth-field-row"><span class="auth-label">Display Name</span></div>', unsafe_allow_html=True)
                reg_name = st.text_input("Display Name", label_visibility="collapsed", placeholder="Jane Doe")

                st.markdown('<div class="auth-field-row"><span class="auth-label">Email</span></div>', unsafe_allow_html=True)
                reg_email = st.text_input(
                    "Email",
                    label_visibility="collapsed",
                    placeholder="you@example.com",
                    key="reg_email",
                )

                st.markdown('<div class="auth-field-row"><span class="auth-label">Password</span></div>', unsafe_allow_html=True)
                reg_password = st.text_input(
                    "Password",
                    label_visibility="collapsed",
                    type="password",
                    key="reg_password",
                    placeholder="Minimum 8 characters",
                )

                st.markdown('<div class="auth-field-row"><span class="auth-label">Confirm Password</span></div>', unsafe_allow_html=True)
                reg_confirm = st.text_input(
                    "Confirm Password",
                    label_visibility="collapsed",
                    type="password",
                    key="reg_confirm",
                )

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
                # Create personal workspace and start 7-day Pro trial
                ws_id = create_personal_workspace(user_id, reg_name)
                from services.workspace_service import start_trial
                start_trial(ws_id, user_id)

                # Auto-login
                from db.queries import get_user_by_id
                user = get_user_by_id(user_id)
                create_user_session(user)
                st.success("Account created! Your 7-day Pro trial has started.")
                st.rerun()

            st.markdown(
                '<div class="auth-bottom">Already have an account? <a class="auth-link" href="?view=login">Sign in</a></div>',
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
