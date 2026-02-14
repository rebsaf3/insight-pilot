"""Billing page — subscription management, credits, top-ups."""

import streamlit as st
from auth.session import require_permission


def show():
    user, ws = require_permission("manage_billing")
    st.title("Billing & Subscription")
    st.info("Billing management coming soon.")


show()
