"""Analysis wizard page — describe, review, save reports."""

import streamlit as st
from auth.session import require_permission


def show():
    user, ws = require_permission("run_analysis")
    st.title("Analyze Data")
    st.info("Analysis wizard coming soon.")


show()
