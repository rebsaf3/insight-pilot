"""File upload page — upload data files and see previews."""

import streamlit as st
from auth.session import require_permission


def show():
    user, ws = require_permission("upload_data")
    st.title("Upload Data")
    st.info("File upload functionality coming soon.")


show()
