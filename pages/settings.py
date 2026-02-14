"""Account settings page — profile, password, 2FA, sessions."""

import streamlit as st

from auth.authenticator import hash_password, verify_password
from auth.session import require_auth, logout
from db import queries
from services.tfa_service import (
    generate_totp_secret, get_totp_qr_code, enable_totp, verify_totp,
    disable_totp, generate_backup_codes, send_email_2fa_code,
)


def show():
    user = require_auth()
    st.title("Account Settings")

    tab_profile, tab_security, tab_tfa, tab_sessions = st.tabs(
        ["Profile", "Password", "Two-Factor Auth", "Sessions"]
    )

    # ------------------------------------------------------------------ Profile
    with tab_profile:
        st.subheader("Profile Information")
        with st.form("profile_form"):
            new_name = st.text_input("Display Name", value=user.display_name)
            new_email = st.text_input("Email", value=user.email, disabled=True,
                                       help="Email cannot be changed")
            submitted = st.form_submit_button("Save Changes", use_container_width=True)
        if submitted:
            if new_name.strip():
                queries.update_user(user.id, display_name=new_name.strip())
                st.success("Profile updated.")
                st.rerun()
            else:
                st.error("Display name cannot be empty.")

        st.divider()
        st.caption(f"**Account created:** {user.created_at[:10]}")
        if user.sso_provider:
            st.caption(f"**SSO provider:** {user.sso_provider.capitalize()}")

        st.divider()
        with st.expander("Danger Zone"):
            st.warning("Deleting your account is permanent and cannot be undone.")
            if st.button("Delete Account", type="primary"):
                st.session_state["confirm_delete_account"] = True
            if st.session_state.get("confirm_delete_account"):
                st.error("This will delete your account, remove you from all workspaces, and delete any workspaces you own.")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Yes, delete my account"):
                        queries.delete_all_user_sessions(user.id)
                        queries.delete_user(user.id)
                        logout()
                        st.rerun()
                with col2:
                    if st.button("Cancel"):
                        st.session_state.pop("confirm_delete_account", None)
                        st.rerun()

    # ------------------------------------------------------------------ Password
    with tab_security:
        st.subheader("Change Password")
        if user.sso_provider and not user.password_hash:
            st.info("Your account uses SSO. You can set a password to enable email+password login as a fallback.")
            with st.form("set_password_form"):
                new_pw = st.text_input("New Password", type="password", help="Minimum 8 characters")
                confirm_pw = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button("Set Password", use_container_width=True)
            if submitted:
                if not new_pw or len(new_pw) < 8:
                    st.error("Password must be at least 8 characters.")
                elif new_pw != confirm_pw:
                    st.error("Passwords do not match.")
                else:
                    queries.update_user(user.id, password_hash=hash_password(new_pw))
                    st.success("Password set successfully.")
        else:
            with st.form("change_password_form"):
                current_pw = st.text_input("Current Password", type="password")
                new_pw = st.text_input("New Password", type="password", help="Minimum 8 characters")
                confirm_pw = st.text_input("Confirm New Password", type="password")
                submitted = st.form_submit_button("Change Password", use_container_width=True)
            if submitted:
                if not current_pw:
                    st.error("Please enter your current password.")
                elif not verify_password(current_pw, user.password_hash):
                    st.error("Current password is incorrect.")
                elif not new_pw or len(new_pw) < 8:
                    st.error("New password must be at least 8 characters.")
                elif new_pw != confirm_pw:
                    st.error("New passwords do not match.")
                else:
                    queries.update_user(user.id, password_hash=hash_password(new_pw))
                    st.success("Password changed successfully.")

    # ------------------------------------------------------------------ 2FA
    with tab_tfa:
        st.subheader("Two-Factor Authentication")

        # TOTP
        st.markdown("### Authenticator App (TOTP)")
        if user.totp_enabled:
            st.success("TOTP is enabled.")
            if st.button("Disable TOTP"):
                disable_totp(user.id)
                st.success("TOTP disabled.")
                st.rerun()
        else:
            if st.button("Set Up TOTP"):
                st.session_state["totp_setup"] = True

            if st.session_state.get("totp_setup"):
                # Generate secret and QR code
                if "totp_secret" not in st.session_state:
                    st.session_state["totp_secret"] = generate_totp_secret()

                secret = st.session_state["totp_secret"]
                qr_image = get_totp_qr_code(secret, user.email)

                st.image(qr_image, caption="Scan with your authenticator app", width=250)
                st.code(secret, language=None)
                st.caption("Or enter the code above manually in your authenticator app.")

                with st.form("verify_totp_setup"):
                    code = st.text_input("Enter the 6-digit code to verify", max_chars=6)
                    submitted = st.form_submit_button("Verify & Enable", use_container_width=True)
                if submitted and code:
                    success, _err = enable_totp(user.id, secret, code)
                    if success:
                        st.session_state.pop("totp_setup", None)
                        st.session_state.pop("totp_secret", None)
                        st.success("TOTP enabled successfully!")

                        # Generate backup codes
                        codes = generate_backup_codes(user.id)
                        st.warning("Save these backup codes in a safe place. Each can only be used once.")
                        for c in codes:
                            st.code(c, language=None)
                        st.rerun()
                    else:
                        st.error("Invalid code. Please try again.")

                if st.button("Cancel Setup"):
                    st.session_state.pop("totp_setup", None)
                    st.session_state.pop("totp_secret", None)
                    st.rerun()

        st.divider()

        # Email 2FA
        st.markdown("### Email Two-Factor")
        if user.email_2fa_enabled:
            st.success("Email 2FA is enabled.")
            if st.button("Disable Email 2FA"):
                queries.update_user(user.id, email_2fa_enabled=0)
                st.success("Email 2FA disabled.")
                st.rerun()
        else:
            st.write("When enabled, a verification code will be sent to your email during login.")
            if st.button("Enable Email 2FA"):
                queries.update_user(user.id, email_2fa_enabled=1)
                st.success("Email 2FA enabled.")
                st.rerun()

        st.divider()

        # Backup codes
        st.markdown("### Backup Codes")
        st.write("Backup codes can be used if you lose access to your authenticator app.")
        if st.button("Generate New Backup Codes"):
            codes = generate_backup_codes(user.id)
            st.warning("Save these codes — they replace any previous backup codes.")
            for c in codes:
                st.code(c, language=None)

    # ------------------------------------------------------------------ Sessions
    with tab_sessions:
        st.subheader("Active Sessions")
        sessions = queries.get_user_sessions(user.id)
        current_token = st.session_state.get("session_token")

        if not sessions:
            st.info("No active sessions found.")
        else:
            for s in sessions:
                is_current = s.session_token == current_token
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    label = "Current session" if is_current else "Session"
                    st.write(f"**{label}**")
                    if s.ip_address:
                        st.caption(f"IP: {s.ip_address}")
                with col2:
                    st.caption(f"Created: {s.created_at[:16]}")
                    st.caption(f"Expires: {s.expires_at[:16]}")
                with col3:
                    if not is_current:
                        if st.button("Revoke", key=f"revoke_session_{s.id}"):
                            queries.delete_session(s.id)
                            st.success("Session revoked.")
                            st.rerun()

            st.divider()
            if st.button("Revoke All Other Sessions"):
                for s in sessions:
                    if s.session_token != current_token:
                        queries.delete_session(s.id)
                st.success("All other sessions revoked.")
                st.rerun()


show()
