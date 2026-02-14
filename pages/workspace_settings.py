"""Workspace settings page — member management, invitations, SSO config."""

import streamlit as st

from auth.session import require_auth, get_current_workspace, user_has_permission
from config.settings import TIERS, ROLE_PERMISSIONS, BASE_URL
from db import queries
from services.workspace_service import invite_member


def show():
    user = require_auth()
    ws = get_current_workspace()
    if not ws:
        st.warning("Please select a workspace.")
        st.stop()

    role = queries.get_member_role(ws.id, user.id)
    is_owner = role == "owner"
    is_admin = role in ("owner", "admin")

    st.title(f"Workspace Settings — {ws.name}")

    tab_general, tab_members, tab_sso = st.tabs(["General", "Members", "SSO"])

    # ------------------------------------------------------------------ General
    with tab_general:
        if is_owner:
            with st.form("ws_general"):
                new_name = st.text_input("Workspace Name", value=ws.name)
                new_desc = st.text_area("Description", value=ws.description, height=100)
                submitted = st.form_submit_button("Save Changes", use_container_width=True)
            if submitted:
                if new_name.strip():
                    queries.update_workspace(ws.id, name=new_name.strip(), description=new_desc.strip())
                    st.success("Workspace updated.")
                    st.rerun()
                else:
                    st.error("Name cannot be empty.")
        else:
            st.write(f"**Name:** {ws.name}")
            st.write(f"**Description:** {ws.description or '—'}")

        st.divider()
        tier_config = TIERS.get(ws.tier, TIERS["free"])
        st.write(f"**Tier:** {tier_config['name']}")
        st.write(f"**Owner:** {_get_user_display(ws.owner_id)}")
        st.write(f"**Created:** {ws.created_at[:10]}")

        if is_owner:
            st.divider()
            with st.expander("Danger Zone", expanded=False):
                st.warning("Deleting a workspace permanently removes all projects, dashboards, and data.")
                if st.button("Delete Workspace", type="primary"):
                    st.session_state["confirm_delete_ws"] = True
                if st.session_state.get("confirm_delete_ws"):
                    st.error("Are you sure? This cannot be undone.")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Yes, delete permanently"):
                            queries.delete_workspace(ws.id)
                            st.session_state.pop("current_workspace_id", None)
                            st.session_state.pop("confirm_delete_ws", None)
                            st.success("Workspace deleted.")
                            st.rerun()
                    with col2:
                        if st.button("Cancel"):
                            st.session_state.pop("confirm_delete_ws", None)
                            st.rerun()

    # ------------------------------------------------------------------ Members
    with tab_members:
        members = queries.get_workspace_members(ws.id)
        tier_config = TIERS.get(ws.tier, TIERS["free"])
        max_members = tier_config["max_members"]

        st.subheader(f"Members ({len(members)}" + (f"/{max_members}" if max_members > 0 else "") + ")")

        for m in members:
            member_user = queries.get_user_by_id(m.user_id)
            if not member_user:
                continue
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"**{member_user.display_name}** ({member_user.email})")
            with col2:
                if is_admin and m.user_id != ws.owner_id and m.user_id != user.id:
                    new_role = st.selectbox(
                        "Role",
                        ["admin", "member", "viewer"],
                        index=["admin", "member", "viewer"].index(m.role) if m.role in ["admin", "member", "viewer"] else 1,
                        key=f"role_{m.user_id}",
                        label_visibility="collapsed",
                    )
                    if new_role != m.role:
                        queries.update_member_role(ws.id, m.user_id, new_role)
                        st.rerun()
                else:
                    st.write(m.role.capitalize())
            with col3:
                if is_admin and m.user_id != ws.owner_id and m.user_id != user.id:
                    if st.button("Remove", key=f"rm_{m.user_id}"):
                        queries.remove_workspace_member(ws.id, m.user_id)
                        st.success(f"Removed {member_user.display_name}")
                        st.rerun()

        # Invite new member
        if is_admin:
            st.divider()
            st.subheader("Invite Member")
            if max_members > 0 and len(members) >= max_members:
                st.info(f"Member limit reached ({max_members}). Upgrade to add more members.")
            else:
                with st.form("invite_form"):
                    invite_email = st.text_input("Email address")
                    invite_role = st.selectbox("Role", ["member", "viewer", "admin"])
                    submitted = st.form_submit_button("Send Invitation", use_container_width=True)
                if submitted and invite_email:
                    success, result = invite_member(ws.id, user.id, invite_email.strip().lower(), invite_role)
                    if success:
                        st.success(f"Invitation sent to {invite_email}. Token: `{result}`")
                    else:
                        st.error(result)

            # Pending invitations
            pending = queries.get_pending_invitations(ws.id)
            if pending:
                st.divider()
                st.subheader("Pending Invitations")
                for inv in pending:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"{inv.email} — {inv.role}")
                    with col2:
                        st.caption(f"Expires: {inv.expires_at[:10]}")
                    with col3:
                        if st.button("Revoke", key=f"revoke_{inv.id}"):
                            queries.revoke_invitation(inv.id)
                            st.success("Invitation revoked.")
                            st.rerun()

    # ------------------------------------------------------------------ SSO
    with tab_sso:
        tier_config = TIERS.get(ws.tier, TIERS["free"])
        available_providers = tier_config.get("sso_providers", [])

        if not available_providers:
            st.info("SSO is available on Pro and Enterprise plans. Upgrade to enable SSO.")
            return

        if not is_admin:
            st.info("Only workspace owners and admins can configure SSO.")
            if ws.sso_enabled:
                st.success("SSO is enabled for this workspace.")
                sso_config = ws.sso_config or {}
                if "google" in available_providers:
                    _show_sso_login_button("google", ws.id)
                if "microsoft" in available_providers:
                    _show_sso_login_button("microsoft", ws.id)
            return

        st.subheader("Single Sign-On (SSO)")
        sso_config = ws.sso_config or {}

        # Google OIDC
        if "google" in available_providers:
            st.markdown("### Google")
            with st.form("google_sso_form"):
                g_client_id = st.text_input(
                    "Google Client ID",
                    value=sso_config.get("google_client_id", ""),
                    help="From Google Cloud Console → APIs & Services → Credentials",
                )
                g_client_secret = st.text_input(
                    "Google Client Secret",
                    value=sso_config.get("google_client_secret", ""),
                    type="password",
                )
                g_submitted = st.form_submit_button("Save Google SSO", use_container_width=True)
            if g_submitted:
                sso_config["google_client_id"] = g_client_id
                sso_config["google_client_secret"] = g_client_secret
                _save_sso(ws.id, sso_config)

            if sso_config.get("google_client_id"):
                callback_url = f"{BASE_URL}/auth/sso/google/callback"
                st.caption(f"Redirect URI: `{callback_url}`")

        # Microsoft OIDC
        if "microsoft" in available_providers:
            st.markdown("### Microsoft (Azure AD)")
            with st.form("microsoft_sso_form"):
                ms_tenant = st.text_input(
                    "Azure AD Tenant ID",
                    value=sso_config.get("microsoft_tenant_id", ""),
                    help="From Azure Portal → Azure Active Directory → Properties",
                )
                ms_client_id = st.text_input(
                    "Application (Client) ID",
                    value=sso_config.get("microsoft_client_id", ""),
                )
                ms_client_secret = st.text_input(
                    "Client Secret",
                    value=sso_config.get("microsoft_client_secret", ""),
                    type="password",
                )
                ms_submitted = st.form_submit_button("Save Microsoft SSO", use_container_width=True)
            if ms_submitted:
                sso_config["microsoft_tenant_id"] = ms_tenant
                sso_config["microsoft_client_id"] = ms_client_id
                sso_config["microsoft_client_secret"] = ms_client_secret
                _save_sso(ws.id, sso_config)

            if sso_config.get("microsoft_client_id"):
                callback_url = f"{BASE_URL}/auth/sso/microsoft/callback"
                st.caption(f"Redirect URI: `{callback_url}`")

        # SAML (Enterprise only)
        if "saml" in available_providers:
            st.markdown("### SAML 2.0")
            with st.form("saml_sso_form"):
                saml_idp_url = st.text_input(
                    "IdP SSO URL",
                    value=sso_config.get("idp_sso_url", ""),
                    help="Your identity provider's Single Sign-On URL (e.g., Okta, OneLogin, Azure AD SAML)",
                )
                saml_idp_cert = st.text_area(
                    "IdP X.509 Certificate",
                    value=sso_config.get("idp_certificate", ""),
                    height=150,
                    help="PEM-formatted certificate from your IdP",
                )
                saml_entity_id = st.text_input(
                    "SP Entity ID (optional)",
                    value=sso_config.get("sp_entity_id", f"{BASE_URL}/auth/sso/saml/metadata"),
                )
                saml_submitted = st.form_submit_button("Save SAML SSO", use_container_width=True)
            if saml_submitted:
                sso_config["idp_sso_url"] = saml_idp_url
                sso_config["idp_certificate"] = saml_idp_cert
                sso_config["sp_entity_id"] = saml_entity_id
                _save_sso(ws.id, sso_config)

            st.caption(f"ACS URL: `{BASE_URL}/auth/sso/saml/acs`")
            st.caption(f"SP Metadata: `{BASE_URL}/auth/sso/saml/metadata`")

        # Enable/disable SSO
        st.divider()
        sso_enabled = st.toggle("Enable SSO for this workspace", value=ws.sso_enabled)
        if sso_enabled != ws.sso_enabled:
            queries.update_workspace(ws.id, sso_enabled=1 if sso_enabled else 0)
            st.success("SSO " + ("enabled" if sso_enabled else "disabled") + ".")
            st.rerun()

        if ws.sso_enabled:
            require_sso = st.toggle(
                "Require SSO for all members (disable password login)",
                value=sso_config.get("require_sso", False),
            )
            if require_sso != sso_config.get("require_sso", False):
                sso_config["require_sso"] = require_sso
                _save_sso(ws.id, sso_config)


def _save_sso(workspace_id: str, sso_config: dict):
    """Save SSO configuration."""
    from services.sso_service import save_workspace_sso_config
    save_workspace_sso_config(workspace_id, sso_config, True)
    st.success("SSO configuration saved.")
    st.rerun()


def _show_sso_login_button(provider: str, workspace_id: str):
    """Show an SSO login button."""
    label = f"Sign in with {provider.capitalize()}"
    if provider == "google":
        from services.sso_service import get_google_auth_url
        url = get_google_auth_url(workspace_id)
    elif provider == "microsoft":
        from services.sso_service import get_microsoft_auth_url
        url = get_microsoft_auth_url(workspace_id)
    else:
        return
    st.link_button(label, url)


def _get_user_display(user_id: str) -> str:
    """Get display name for a user."""
    u = queries.get_user_by_id(user_id)
    return u.display_name if u else "Unknown"


show()
