"""Dashboard edit page — reorder, delete, manage charts."""

import streamlit as st
from auth.session import require_permission


def show():
    user, ws = require_permission("create_edit_dashboards")
    st.title("Edit Dashboard")
    st.info("Dashboard editing coming soon.")


show()
