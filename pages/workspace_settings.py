"""Workspace settings page — member management, invitations, SSO config."""

import streamlit as st
from auth.session import require_permission


def show():
    user, ws = require_permission("invite_remove_members")
    st.title("Workspace Settings")
    st.info("Workspace management coming soon.")


show()
