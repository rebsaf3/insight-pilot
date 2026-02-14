"""Branding page — logo, colors, fonts, chart styling."""

import streamlit as st
from auth.session import require_permission


def show():
    user, ws = require_permission("manage_branding")
    st.title("Branding & Styling")
    st.info("Branding customization coming soon.")


show()
