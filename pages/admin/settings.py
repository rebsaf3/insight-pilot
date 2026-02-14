"""Admin — System Configuration page."""

import json
import streamlit as st

from auth.session import require_superadmin
from db import queries


def show():
    admin = require_superadmin()

    st.title("System Configuration")
    st.caption("Manage global platform settings and feature flags")

    tab1, tab2 = st.tabs(["Settings", "Default Prompts"])

    with tab1:
        st.subheader("System Settings")
        st.info("Settings are stored as key-value pairs. Changes take effect immediately.")

        # Load current settings
        settings = queries.get_all_system_settings()

        # Pre-defined settings with defaults
        setting_definitions = [
            ("maintenance_mode", "Maintenance Mode", "false", "Set to 'true' to show maintenance banner"),
            ("signup_enabled", "User Registration", "true", "Set to 'false' to disable new signups"),
            ("max_workspaces_per_user", "Max Workspaces Per User", "5", "Maximum workspaces a user can own"),
            ("global_rate_limit", "Global API Rate Limit", "100", "Requests per minute per API key"),
            ("announcement", "Platform Announcement", "", "Banner message shown to all users"),
        ]

        with st.form("system_settings"):
            values = {}
            for key, label, default, help_text in setting_definitions:
                current = settings.get(key, default)
                values[key] = st.text_input(label, value=current, help=help_text)

            if st.form_submit_button("Save Settings", use_container_width=True, type="primary"):
                for key, value in values.items():
                    queries.set_system_setting(key, value, admin.id)
                queries.create_audit_log(
                    user_id=admin.id,
                    action="update_settings",
                    entity_type="system",
                    details={"updated_keys": list(values.keys())},
                )
                st.success("Settings saved!")
                st.rerun()

        # Custom settings
        st.divider()
        st.subheader("Custom Settings")

        with st.form("custom_setting"):
            new_key = st.text_input("Key", placeholder="custom.feature_flag")
            new_value = st.text_input("Value", placeholder="true")
            if st.form_submit_button("Add Setting"):
                if new_key and new_value:
                    queries.set_system_setting(new_key, new_value, admin.id)
                    st.success(f"Setting '{new_key}' saved!")
                    st.rerun()

        # Show all current settings
        if settings:
            st.markdown("**All Current Settings:**")
            for k, v in sorted(settings.items()):
                st.caption(f"`{k}` = `{v}`")

    with tab2:
        st.subheader("Default System Prompt Override")
        st.info("Override the default system prompt for all projects. Leave empty to use the built-in prompt.")

        current_override = queries.get_system_setting("default_system_prompt_override") or ""
        new_override = st.text_area(
            "System Prompt Override",
            value=current_override,
            height=200,
            placeholder="Leave empty to use the default InsightPilot system prompt...",
        )

        if st.button("Save Prompt Override", type="primary"):
            queries.set_system_setting("default_system_prompt_override", new_override, admin.id)
            st.success("Prompt override saved!")


show()
