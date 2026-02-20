"""Account settings page — profile, password, 2FA, preferences, team, sessions."""

import streamlit as st

from auth.authenticator import hash_password, verify_password
from auth.session import require_auth, logout, get_current_workspace
from db import queries
from services.tfa_service import (
    generate_totp_secret, get_totp_qr_code, enable_totp, verify_totp,
    disable_totp, generate_backup_codes, send_email_2fa_code,
)


def show():
    user = require_auth()
    st.title("Account Settings")
    st.info("⚙️ Manage your profile, password, two-factor authentication, and notification preferences here.")

    tab_profile, tab_security, tab_tfa, tab_prefs, tab_team, tab_sessions = st.tabs(
        ["Profile", "Password", "Two-Factor Auth", "Preferences", "Team", "Sessions"]
    )

    # ------------------------------------------------------------------ Profile
    with tab_profile:
        st.subheader("Profile Information")
        # Avatar display and upload
        st.markdown("#### Profile Picture")
        avatar_url = user.avatar_url or "https://ui-avatars.com/api/?name=" + (user.display_name or user.email)
        st.image(avatar_url, width=96, caption="Current Avatar")
        with st.form("avatar_upload_form"):
            uploaded_avatar = st.file_uploader("Upload new avatar", type=["png", "jpg", "jpeg", "gif"], accept_multiple_files=False)
            avatar_submit = st.form_submit_button("Update Avatar", use_container_width=True)
        if avatar_submit and uploaded_avatar:
            from pathlib import Path
            import uuid
            ext = Path(uploaded_avatar.name).suffix.lower()
            if ext not in [".png", ".jpg", ".jpeg", ".gif"]:
                st.error("Unsupported file type.")
            else:
                avatar_dir = "storage/uploads/avatars"
                Path(avatar_dir).mkdir(parents=True, exist_ok=True)
                avatar_filename = f"{user.id}_{uuid.uuid4().hex}{ext}"
                avatar_path = Path(avatar_dir) / avatar_filename
                avatar_path.write_bytes(uploaded_avatar.read())
                avatar_url = f"/{avatar_dir}/{avatar_filename}"
                queries.update_user(user.id, avatar_url=avatar_url)
                st.success("Avatar updated.")
                st.rerun()

        with st.form("profile_form"):
            col_fn, col_ln = st.columns(2)
            first_name = col_fn.text_input(
                "First Name",
                value=getattr(user, "first_name", "") or "",
            )
            last_name = col_ln.text_input(
                "Last Name",
                value=getattr(user, "last_name", "") or "",
            )
            new_name = st.text_input("Display Name", value=user.display_name)
            new_email = st.text_input("Email", value=user.email, disabled=True,
                                       help="Email cannot be changed")
            submitted = st.form_submit_button("Save Changes", use_container_width=True)
        if submitted:
            if new_name.strip():
                queries.update_user(
                    user.id,
                    display_name=new_name.strip(),
                    first_name=first_name.strip(),
                    last_name=last_name.strip(),
                )
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

    # ------------------------------------------------------------------ Preferences
    from components.theme import inject_custom_css
    with tab_prefs:
        st.subheader("Preferences")

        prefs = queries.get_user_preferences(user.id)
        current_theme = prefs.theme if prefs else "light"
        current_notif_email = prefs.notification_email if prefs else True
        current_notif_in_app = getattr(prefs, "notification_in_app", True) if prefs else True
        current_notif_billing = prefs.notification_billing if prefs else True
        current_notif_product = prefs.notification_product if prefs else True

        # Inject theme CSS
        inject_custom_css(theme=current_theme)

        st.markdown("### Appearance")
        theme = st.selectbox(
            "Theme",
            ["light", "dark"],
            index=0 if current_theme == "light" else 1,
            format_func=lambda t: "Light" if t == "light" else "Dark",
            help="Changes the app color scheme. Reload may be required.",
        )

        st.markdown("### Accessibility")
        accessibility_options = st.multiselect(
            "Accessibility options",
            ["High contrast", "Large text", "Screen reader support"],
            help="Choose accessibility features to improve usability."
        )

        st.markdown("### Notifications")
        notif_email = st.toggle(
            "Email notifications",
            value=current_notif_email,
            help="Receive email notifications for important events",
        )
        notif_in_app = st.toggle(
            "In-app notifications",
            value=current_notif_in_app,
            help="Show notifications in the app UI",
        )
        notif_billing = st.toggle(
            "Billing notifications",
            value=current_notif_billing,
            help="Get notified about billing events (credit low, subscription renewals)",
        )
        notif_product = st.toggle(
            "Product updates",
            value=current_notif_product,
            help="Receive updates about new features and improvements",
        )

        if st.button("Save Preferences", type="primary", use_container_width=True):
            queries.upsert_user_preferences(
                user.id,
                theme=theme,
                notification_email=1 if notif_email else 0,
                notification_in_app=1 if notif_in_app else 0,
                notification_billing=1 if notif_billing else 0,
                notification_product=1 if notif_product else 0,
                accessibility_options=accessibility_options,
            )
            st.success("Preferences saved.")
            st.rerun()

    # ------------------------------------------------------------------ Team
    with tab_team:
        _show_team_tab(user)

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


def _show_team_tab(user):
    """Team management — view members, invite, change roles."""
    st.subheader("Team Members")

    ws = get_current_workspace()
    if not ws:
        st.warning("No workspace selected.")
        return

    role = queries.get_member_role(ws.id, user.id)
    is_admin = role in ("owner", "admin")

    # List members
    members = queries.get_workspace_members(ws.id)
    for m in members:
        member_user = queries.get_user_by_id(m.user_id)
        if not member_user:
            continue

        role_mapping = {
            "owner": ("ip-badge ip-badge-info", "Owner"),
            "admin": ("ip-badge ip-badge-success", "Admin"),
            "member": ("ip-badge ip-badge-pending", "Member"),
            "viewer": ("ip-badge", "Viewer"),
        }
        cls, label = role_mapping.get(m.role, ("ip-badge", m.role.title()))

        st.markdown(
            f"<div class='ip-card' style='display:flex;align-items:center;gap:1rem;"
            f"padding:0.75rem 1rem;margin-bottom:0.5rem'>"
            f"<div style='flex:1'>"
            f"<div style='font-weight:600;font-size:0.9rem'>"
            f"{member_user.display_name}</div>"
            f"<div style='font-size:0.78rem;color:#57534E'>{member_user.email}</div>"
            f"</div>"
            f"<span class='{cls}'>{label}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Admin actions (not for self, not for owner)
        if is_admin and m.user_id != user.id and m.role != "owner":
            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                new_role = st.selectbox(
                    "Role",
                    ["admin", "member", "viewer"],
                    index=["admin", "member", "viewer"].index(m.role) if m.role in ("admin", "member", "viewer") else 1,
                    key=f"role_{m.user_id}",
                    label_visibility="collapsed",
                )
                if new_role != m.role:
                    if st.button("Update Role", key=f"update_role_{m.user_id}"):
                        queries.update_member_role(ws.id, m.user_id, new_role)
                        st.success(f"Role updated to {new_role}.")
                        st.rerun()
            with ac2:
                if st.button("Reset Password", key=f"reset_pw_{m.user_id}"):
                    st.session_state[f"confirm_reset_pw_{m.user_id}"] = True
                if st.session_state.get(f"confirm_reset_pw_{m.user_id}"):
                    temp_pw = st.text_input(
                        "Set temporary password",
                        type="password",
                        key=f"temp_pw_{m.user_id}",
                        placeholder="Min 8 characters",
                    )
                    rc1, rc2 = st.columns(2)
                    if rc1.button("Confirm", key=f"confirm_pw_{m.user_id}"):
                        if temp_pw and len(temp_pw) >= 8:
                            queries.update_user(m.user_id, password_hash=hash_password(temp_pw))
                            st.session_state.pop(f"confirm_reset_pw_{m.user_id}", None)
                            st.success(f"Password reset for {member_user.display_name}.")
                            st.rerun()
                        else:
                            st.error("Password must be at least 8 characters.")
                    if rc2.button("Cancel", key=f"cancel_pw_{m.user_id}"):
                        st.session_state.pop(f"confirm_reset_pw_{m.user_id}", None)
                        st.rerun()
            with ac3:
                if st.button("Remove", key=f"remove_{m.user_id}"):
                    queries.remove_workspace_member(ws.id, m.user_id)
                    st.success("Member removed.")
                    st.rerun()

    # Invite form (admin only)
    if is_admin:
        st.divider()
        st.markdown("### Invite Member")
        with st.form("invite_member_form"):
            invite_email = st.text_input("Email address", placeholder="colleague@company.com")
            invite_role = st.selectbox("Role", ["member", "admin", "viewer"])
            invite_submitted = st.form_submit_button("Send Invitation", use_container_width=True)

        if invite_submitted and invite_email:
            from services.workspace_service import invite_member
            success, result = invite_member(ws.id, invite_email, invite_role, user.id)
            if success:
                st.success(f"Invitation sent to {invite_email}.")
            else:
                st.error(result)

    # Pending invitations
    if is_admin:
        pending = queries.get_pending_invitations(ws.id)
        if pending:
            st.divider()
            st.markdown("### Pending Invitations")
            for inv in pending:
                ic1, ic2, ic3 = st.columns([3, 1, 1])
                ic1.markdown(f"**{inv.email}** — {inv.role}")
                ic2.caption(f"Expires: {inv.expires_at[:10]}")
                if ic3.button("Revoke", key=f"revoke_inv_{inv.id}"):
                    queries.revoke_invitation(inv.id)
                    st.success("Invitation revoked.")
                    st.rerun()


show()
