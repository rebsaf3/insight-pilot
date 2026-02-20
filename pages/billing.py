"""Billing page — subscription management, credit bundles, add-ons, payment methods."""

import streamlit as st

from auth.session import require_permission
from services import credit_service, stripe_service
from services.workspace_service import check_trial_status, get_trial_days_remaining
from config.settings import TIERS, CREDIT_BUNDLES, AVAILABLE_ADDONS
from db import queries


def show():
    user, ws = require_permission("manage_billing")

    st.title("Billing & Subscription")
    st.info("💳 Manage your subscription, payment methods, and view billing history here.")

    # ----- Trial banner at top -----
    _show_trial_status(ws)

    # ----- Current plan overview -----
    tier_config = TIERS.get(ws.tier, TIERS["free"])
    usage = credit_service.get_usage_summary(ws.id, user.id)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Plan", tier_config["name"])
    col2.metric("Credits", usage["credits_remaining"])
    col3.metric("Uploads", f"{usage['uploads_today']}/{usage['uploads_limit'] if usage['uploads_limit'] != -1 else '\u221e'}")
    col4.metric("Dashboards", f"{usage['dashboards_count']}/{usage['dashboards_limit'] if usage['dashboards_limit'] != -1 else '\u221e'}")

    # Credit usage bar
    if usage["monthly_allowance"] > 0:
        used = usage["monthly_allowance"] - usage["credits_remaining"]
        pct = min(1.0, max(0.0, used / usage["monthly_allowance"]))
        st.progress(pct, text=f"{used}/{usage['monthly_allowance']} credits used this month")

    st.divider()

    # ----- Plan comparison -----
    st.markdown("<div class='ip-section-header'><h3>Plans</h3></div>", unsafe_allow_html=True)
    plan_cols = st.columns(3)

    for col, (tier_key, config) in zip(plan_cols, TIERS.items()):
        with col:
            is_current = ws.tier == tier_key
            price_label = f"${config['price_monthly']}/mo" if config["price_monthly"] > 0 else "Free"
            badge_html = ""
            if is_current:
                badge_html = "<span class='ip-badge ip-badge-success' style='margin-left:8px'>Current</span>"

            st.markdown(
                f"<div class='ip-card' style='text-align:center;padding:1.25rem'>"
                f"<div style='font-weight:700;font-size:1.1rem;margin-bottom:0.25rem'>"
                f"{config['name']}{badge_html}</div>"
                f"<div style='font-size:1.5rem;font-weight:700;color:#0F766E;margin-bottom:0.75rem'>"
                f"{price_label}</div>"
                f"<div style='font-size:0.82rem;color:#57534E;text-align:left;line-height:1.8'>"
                f"\u2022 {config['monthly_credits']} credits/mo<br>"
                f"\u2022 {config['uploads_per_day'] if config['uploads_per_day'] != -1 else 'Unlimited'} uploads/day<br>"
                f"\u2022 {config['max_dashboards'] if config['max_dashboards'] != -1 else 'Unlimited'} dashboards<br>"
                f"\u2022 {'Unlimited revisions' if config['max_revisions_per_report'] == -1 else 'No revisions'}<br>"
                f"\u2022 {'PDF/PNG export' if config['export_enabled'] else 'No export'}<br>"
                f"\u2022 {config['max_members'] if config['max_members'] != -1 else 'Unlimited'} members"
                f"</div></div>",
                unsafe_allow_html=True,
            )

            if not is_current and config["price_monthly"] > 0:
                if st.button(f"Upgrade to {config['name']}", key=f"upgrade_{tier_key}", use_container_width=True, type="primary"):
                    try:
                        url = stripe_service.create_subscription_checkout(user.email, ws.id, tier_key)
                        st.markdown(f"[Complete checkout]({url})")
                    except Exception as e:
                        st.error(f"Error creating checkout: {e}")

    st.divider()

    # ----- Credit Bundles -----
    st.markdown("<div class='ip-section-header'><h3>Buy Credits</h3></div>", unsafe_allow_html=True)

    if not tier_config.get("topup_enabled"):
        st.info("Credit top-ups are available on Pro and Enterprise plans.")
    else:
        bundle_cols = st.columns(len(CREDIT_BUNDLES))
        for col, bundle in zip(bundle_cols, CREDIT_BUNDLES):
            with col:
                badge_html = ""
                if bundle.get("badge"):
                    badge_html = (
                        f"<div style='position:absolute;top:-8px;right:12px'>"
                        f"<span class='ip-badge ip-badge-info'>{bundle['badge']}</span></div>"
                    )

                price_dollars = bundle["price_cents"] / 100
                st.markdown(
                    f"<div class='ip-card ip-card-hover' style='text-align:center;"
                    f"position:relative;padding:1.25rem 1rem'>"
                    f"{badge_html}"
                    f"<div style='font-weight:700;font-size:1.5rem;color:#0F766E'>"
                    f"{bundle['credits']}</div>"
                    f"<div style='font-size:0.72rem;color:#57534E;text-transform:uppercase;"
                    f"letter-spacing:0.06em;font-weight:500;margin-bottom:0.5rem'>Credits</div>"
                    f"<div style='font-size:1.1rem;font-weight:700;margin-bottom:0.25rem'>"
                    f"${price_dollars:.0f}</div>"
                    f"<div style='font-size:0.75rem;color:#A8A29E'>{bundle['per_credit']}/credit</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if st.button(f"Buy {bundle['credits']}", key=f"buy_{bundle['credits']}", use_container_width=True):
                    try:
                        url = stripe_service.create_bundle_checkout(user.email, ws.id, user.id, bundle)
                        st.markdown(f"[Complete purchase]({url})")
                    except Exception as e:
                        st.error(f"Error: {e}")

    st.divider()

    # ----- Add-Ons -----
    st.markdown("<div class='ip-section-header'><h3>Add-Ons</h3></div>", unsafe_allow_html=True)

    addon_cols = st.columns(len(AVAILABLE_ADDONS))
    for col, addon_def in zip(addon_cols, AVAILABLE_ADDONS):
        with col:
            existing = queries.get_add_on(ws.id, addon_def["type"])
            is_active = existing is not None
            status_html = (
                "<span class='ip-badge ip-badge-success'>Active</span>"
                if is_active
                else ""
            )

            st.markdown(
                f"<div class='ip-card' style='text-align:center;padding:1.25rem 1rem'>"
                f"<div style='margin-bottom:0.25rem'>"
                f"<span class='material-symbols-rounded' style='font-size:2rem;color:#0F766E'>"
                f"{addon_def['icon']}</span></div>"
                f"<div style='font-weight:700;font-size:0.95rem;margin-bottom:0.25rem'>"
                f"{addon_def['name']} {status_html}</div>"
                f"<div style='font-size:0.82rem;color:#57534E;margin-bottom:0.5rem'>"
                f"{addon_def['description']}</div>"
                f"<div style='font-weight:700;color:#0F766E'>"
                f"${addon_def['price_monthly']}/mo</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            if is_active:
                st.button("Active", key=f"addon_{addon_def['type']}", disabled=True, use_container_width=True)
            elif tier_config.get("api_addon_available") or addon_def["type"] != "api_access":
                if st.button(f"Add {addon_def['name']}", key=f"addon_{addon_def['type']}", use_container_width=True):
                    try:
                        url = stripe_service.create_addon_checkout(user.email, ws.id, addon_def["type"])
                        st.markdown(f"[Complete purchase]({url})")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.button("Upgrade to unlock", key=f"addon_{addon_def['type']}", disabled=True, use_container_width=True)

    st.divider()

    # ----- Payment Methods -----
    st.markdown("<div class='ip-section-header'><h3>Payment Methods</h3></div>", unsafe_allow_html=True)

    methods = stripe_service.get_payment_methods(ws.id)
    if methods:
        for m in methods:
            st.markdown(
                f"<div class='ip-card' style='display:flex;align-items:center;gap:1rem;"
                f"padding:0.75rem 1rem;margin-bottom:0.5rem'>"
                f"<div><span class='material-symbols-rounded' style='font-size:1.5rem;color:#0F766E'>credit_card</span></div>"
                f"<div style='flex:1'>"
                f"<div style='font-weight:600;font-size:0.9rem'>{m['brand']} ending in {m['last4']}</div>"
                f"<div style='font-size:0.78rem;color:#57534E'>Expires {m['exp_month']:02d}/{m['exp_year']}</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No payment methods on file.")

    if st.button("Manage Payment Methods", use_container_width=True, icon=":material/credit_card:"):
        portal_url = stripe_service.create_billing_portal_url(ws.id)
        if portal_url:
            st.markdown(f"[Open billing portal]({portal_url})")
        else:
            st.info("Set up billing by upgrading your plan or purchasing credits first.")

    st.divider()

    # ----- Credit History -----
    st.markdown("<div class='ip-section-header'><h3>Credit History</h3></div>", unsafe_allow_html=True)
    history = queries.get_credit_history(ws.id, limit=20)
    if history:
        for entry in history:
            sign = "+" if entry.change_amount > 0 else ""
            color = "#059669" if entry.change_amount > 0 else "#DC2626"
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:0.75rem;padding:0.4rem 0;"
                f"border-bottom:1px solid #F5F5F4;font-family:Inter,sans-serif'>"
                f"<div style='flex:1;font-size:0.85rem'>{entry.reason}</div>"
                f"<div style='font-weight:600;color:{color};font-size:0.88rem'>"
                f"{sign}{entry.change_amount}</div>"
                f"<div style='font-size:0.72rem;color:#A8A29E;min-width:110px;text-align:right'>"
                f"{entry.created_at[:16]}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No credit history yet.")

    # Cancel subscription
    if ws.tier != "free" and check_trial_status(ws.id) != "active":
        st.divider()
        with st.expander("Cancel Subscription"):
            st.warning("Cancelling will downgrade you to the Free plan at the end of your billing period.")
            if st.button("Cancel Subscription", type="secondary"):
                stripe_service.cancel_subscription(ws.id)
                st.success("Subscription will be cancelled at the end of the current period.")


def _show_trial_status(ws) -> None:
    """Show trial status banner at top of billing page."""
    trial_status = check_trial_status(ws.id)
    if trial_status == "active":
        days = get_trial_days_remaining(ws.id)
        day_word = "day" if days == 1 else "days"
        st.markdown(
            f"<div class='ip-trial-banner' style='margin-bottom:1.5rem'>"
            f"<div style='display:flex;align-items:center;justify-content:space-between'>"
            f"<div>"
            f"<div class='label'>&#x1F680; Pro Trial Active</div>"
            f"<div class='days'>{days} {day_word} remaining — "
            f"Enjoying Pro features including 500 credits/mo, unlimited revisions, and exports</div>"
            f"</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
    elif trial_status == "expired" and ws.tier == "free":
        st.markdown(
            "<div style='background:#FEF2F2;border:1px solid #FECACA;border-radius:10px;"
            "padding:12px 16px;margin-bottom:1.5rem;font-family:Inter,sans-serif'>"
            "<div style='font-weight:700;color:#DC2626;margin-bottom:4px'>"
            "Your Pro trial has ended</div>"
            "<div style='font-size:0.88rem;color:#57534E'>"
            "Upgrade to Pro to keep access to unlimited revisions, exports, and more credits.</div>"
            "</div>",
            unsafe_allow_html=True,
        )


show()
