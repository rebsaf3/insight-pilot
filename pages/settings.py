"""Account settings page — profile, password, 2FA, sessions."""

import streamlit as st
from auth.session import require_auth


def show():
    user = require_auth()
    st.title("Account Settings")
    st.info("Account settings coming soon.")


show()
