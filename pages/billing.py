"""Billing page — subscription management, credits, top-ups."""

import streamlit as st

from auth.session import require_permission
from services import credit_service, stripe_service
from config.settings import TIERS
from db import queries


def show():
    user, ws = require_permission("manage_billing")

    st.title("Billing & Subscription")

    # Current plan info
    tier_config = TIERS.get(ws.tier, TIERS["free"])
    usage = credit_service.get_usage_summary(ws.id, user.id)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Plan", tier_config["name"])
    col2.metric("Credits Remaining", usage["credits_remaining"])
    col3.metric("Uploads Today", f"{usage['uploads_today']}/{usage['uploads_limit'] if usage['uploads_limit'] != -1 else '∞'}")
    col4.metric("Dashboards", f"{usage['dashboards_count']}/{usage['dashboards_limit'] if usage['dashboards_limit'] != -1 else '∞'}")

    # Credit usage bar
    if usage["monthly_allowance"] > 0:
        used = usage["monthly_allowance"] - usage["credits_remaining"]
        pct = min(1.0, max(0.0, used / usage["monthly_allowance"]))
        st.progress(pct, text=f"{used}/{usage['monthly_allowance']} credits used this month")

    st.divider()

    # Plan comparison
    st.subheader("Plans")
    plan_cols = st.columns(3)

    for col, (tier_key, config) in zip(plan_cols, TIERS.items()):
        with col:
            is_current = ws.tier == tier_key
            st.markdown(f"### {config['name']}")
            st.markdown(f"**{'$' + str(config['price_monthly']) + '/mo' if config['price_monthly'] > 0 else 'Free'}**")
            st.markdown(f"- {config['monthly_credits']} credits/mo")
            st.markdown(f"- {config['uploads_per_day'] if config['uploads_per_day'] != -1 else 'Unlimited'} uploads/day")
            st.markdown(f"- {config['max_dashboards'] if config['max_dashboards'] != -1 else 'Unlimited'} dashboards")
            st.markdown(f"- {'Unlimited revisions' if config['max_revisions_per_report'] == -1 else 'No revisions'}")
            st.markdown(f"- {'PDF/PNG export' if config['export_enabled'] else 'No export'}")
            st.markdown(f"- {config['max_members'] if config['max_members'] != -1 else 'Unlimited'} members")

            branding_desc = {"none": "Default theme", "basic": "Custom branding", "full": "White-label"}
            st.markdown(f"- {branding_desc.get(config['branding_level'], 'Default')}")

            if is_current:
                st.success("Current Plan")
            elif config["price_monthly"] > 0:
                if st.button(f"Upgrade to {config['name']}", key=f"upgrade_{tier_key}", use_container_width=True):
                    try:
                        url = stripe_service.create_subscription_checkout(user.email, ws.id, tier_key)
                        st.markdown(f"[Complete checkout]({url})")
                    except Exception as e:
                        st.error(f"Error creating checkout: {e}")

    st.divider()

    # Credit top-ups
    if tier_config.get("topup_enabled"):
        st.subheader("Buy More Credits")
        st.markdown("**100 credits — $10.00**")
        if st.button("Purchase Credits", use_container_width=True):
            try:
                url = stripe_service.create_topup_checkout(user.email, ws.id, user.id)
                st.markdown(f"[Complete purchase]({url})")
            except Exception as e:
                st.error(f"Error: {e}")

    # Add-ons
    st.divider()
    st.subheader("Add-Ons")

    api_addon = queries.get_add_on(ws.id, "api_access")
    if api_addon:
        st.success("API Access — Active ($15/mo)")
    elif tier_config.get("api_addon_available"):
        st.markdown("**API Access** — $15/mo — Full REST API for data push and CRUD")
        if st.button("Add API Access", use_container_width=True):
            try:
                url = stripe_service.create_addon_checkout(user.email, ws.id, "api_access")
                st.markdown(f"[Complete purchase]({url})")
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.info("API Access is available on Pro and Enterprise plans.")

    # Credit history
    st.divider()
    st.subheader("Credit History")
    history = queries.get_credit_history(ws.id, limit=20)
    if history:
        for entry in history:
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.markdown(entry.reason)
            col2.markdown(f"{'+'if entry.change_amount > 0 else ''}{entry.change_amount}")
            col3.caption(entry.created_at[:16])
    else:
        st.info("No credit history yet.")

    # Cancel subscription
    if ws.tier != "free":
        st.divider()
        with st.expander("Cancel Subscription"):
            st.warning("Cancelling will downgrade you to the Free plan at the end of your billing period.")
            if st.button("Cancel Subscription", type="secondary"):
                stripe_service.cancel_subscription(ws.id)
                st.success("Subscription will be cancelled at the end of the current period.")


show()
