"""Dashboard view page — render saved dashboards."""

import streamlit as st
from auth.session import require_permission


def show():
    user, ws = require_permission("view_dashboards")
    st.title("Dashboard")
    st.info("Dashboard view coming soon.")


show()
