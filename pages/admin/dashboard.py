"""Product Owner Dashboard — KPIs and system overview."""

import streamlit as st

from auth.session import require_superadmin
from services.admin_service import get_dashboard_kpis


def show():
    user = require_superadmin()

    st.title("Product Owner Dashboard")
    st.caption("System-wide metrics and overview")

    kpis = get_dashboard_kpis()

    # Row 1: Core counts
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Users", kpis["total_users"])
    col2.metric("Total Workspaces", kpis["total_workspaces"])
    col3.metric("Total API Calls", f"{kpis['total_api_calls']:,}")

    # Row 2: Financial
    col4, col5, col6 = st.columns(3)
    col4.metric("Credits Consumed", f"{kpis['total_credits_consumed']:,}")
    col5.metric("Revenue", f"${kpis['total_revenue_cents'] / 100:,.2f}")

    subs = kpis["subscriptions_by_tier"]
    col6.metric("Active Subscriptions", sum(subs.values()) if subs else 0)

    st.divider()

    # Subscriptions by tier
    st.subheader("Subscriptions by Tier")
    if subs:
        tier_cols = st.columns(len(subs))
        for i, (tier, count) in enumerate(sorted(subs.items())):
            tier_cols[i].metric(tier.capitalize(), count)
    else:
        st.info("No active subscriptions yet.")

    st.divider()

    # Quick links
    st.subheader("Quick Actions")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.page_link("pages/admin/users.py", label="Manage Users", icon=":material/people:")
    with c2:
        st.page_link("pages/admin/workspaces.py", label="Manage Workspaces", icon=":material/workspaces:")
    with c3:
        st.page_link("pages/admin/audit.py", label="View Audit Log", icon=":material/history:")


show()
