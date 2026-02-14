"""Admin — Billing & Subscriptions page."""

import streamlit as st

from auth.session import require_superadmin
from db import queries


def show():
    require_superadmin()

    st.title("Billing & Subscriptions")
    st.caption("Platform-wide subscription and revenue overview")

    # Revenue summary
    total_revenue = queries.get_total_revenue_cents()
    subs_by_tier = queries.count_subscriptions_by_tier()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue", f"${total_revenue / 100:,.2f}")
    col2.metric("Active Subscriptions", sum(subs_by_tier.values()) if subs_by_tier else 0)
    col3.metric("Credit Purchases", len(queries.get_all_credit_purchases(limit=10000)))

    st.divider()

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Active Subscriptions", "Credit Purchases", "Credit Ledger"])

    with tab1:
        st.subheader("Active Subscriptions")
        subscriptions = queries.get_all_subscriptions(status="active")
        if not subscriptions:
            st.info("No active subscriptions.")
        else:
            for sub in subscriptions:
                ws = queries.get_workspace_by_id(sub.workspace_id)
                ws_name = ws.name if ws else "Unknown"
                col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
                with col1:
                    st.markdown(f"**{ws_name}**")
                with col2:
                    st.caption(sub.tier.capitalize())
                with col3:
                    st.caption(f"{sub.monthly_credit_allowance} credits/mo")
                with col4:
                    period = f"{sub.current_period_start[:10] if sub.current_period_start else '?'} to {sub.current_period_end[:10] if sub.current_period_end else '?'}"
                    st.caption(period)

    with tab2:
        st.subheader("Credit Purchases")
        purchases = queries.get_all_credit_purchases(limit=50)
        if not purchases:
            st.info("No credit purchases yet.")
        else:
            for p in purchases:
                ws = queries.get_workspace_by_id(p.workspace_id)
                user = queries.get_user_by_id(p.purchased_by)
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                with col1:
                    st.caption(ws.name if ws else "Unknown")
                with col2:
                    st.caption(user.email if user else p.purchased_by)
                with col3:
                    st.caption(f"+{p.credits_purchased} credits")
                with col4:
                    st.caption(f"${p.amount_paid_cents / 100:.2f}")

    with tab3:
        st.subheader("Recent Credit Transactions")
        entries = queries.get_all_credit_ledger(limit=50)
        if not entries:
            st.info("No credit transactions yet.")
        else:
            for e in entries:
                ws = queries.get_workspace_by_id(e.workspace_id)
                color = "green" if e.change_amount > 0 else "red"
                sign = "+" if e.change_amount > 0 else ""
                col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
                with col1:
                    st.caption(ws.name if ws else "Unknown")
                with col2:
                    st.markdown(f":{color}[{sign}{e.change_amount}]")
                with col3:
                    st.caption(e.reason)
                with col4:
                    st.caption(e.created_at[:16] if e.created_at else "")


show()
