"""Stripe integration — subscriptions, checkout, top-ups, webhooks."""

from typing import Optional

import stripe

from config.settings import (
    STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, BASE_URL,
    STRIPE_PRO_PRICE_ID, STRIPE_ENTERPRISE_PRICE_ID,
    STRIPE_API_ADDON_PRICE_ID, STRIPE_TOPUP_PRICE_ID, TIERS,
)
from db import queries
from services import credit_service

stripe.api_key = STRIPE_SECRET_KEY

# ---------------------------------------------------------------------------
# Customer management
# ---------------------------------------------------------------------------

def create_customer(user_email: str, workspace_id: str) -> str:
    """Create a Stripe customer for a workspace. Returns Stripe customer ID."""
    customer = stripe.Customer.create(
        email=user_email,
        metadata={"workspace_id": workspace_id},
    )
    queries.update_workspace(workspace_id, stripe_customer_id=customer.id)
    return customer.id


def get_or_create_customer(user_email: str, workspace_id: str) -> str:
    """Get existing or create new Stripe customer."""
    ws = queries.get_workspace_by_id(workspace_id)
    if ws and ws.stripe_customer_id:
        return ws.stripe_customer_id
    return create_customer(user_email, workspace_id)


# ---------------------------------------------------------------------------
# Checkout sessions
# ---------------------------------------------------------------------------

def create_subscription_checkout(user_email: str, workspace_id: str, tier: str) -> str:
    """Create a Stripe Checkout session for a subscription. Returns checkout URL."""
    customer_id = get_or_create_customer(user_email, workspace_id)

    price_id = {
        "pro": STRIPE_PRO_PRICE_ID,
        "enterprise": STRIPE_ENTERPRISE_PRICE_ID,
    }.get(tier)

    if not price_id:
        raise ValueError(f"No Stripe price configured for tier: {tier}")

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{BASE_URL}/?checkout=success",
        cancel_url=f"{BASE_URL}/?checkout=cancel",
        metadata={"workspace_id": workspace_id, "tier": tier},
    )
    return session.url


def create_topup_checkout(user_email: str, workspace_id: str, user_id: str) -> str:
    """Create a Stripe Checkout session for a credit top-up. Returns checkout URL."""
    customer_id = get_or_create_customer(user_email, workspace_id)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="payment",
        line_items=[{"price": STRIPE_TOPUP_PRICE_ID, "quantity": 1}],
        success_url=f"{BASE_URL}/?topup=success",
        cancel_url=f"{BASE_URL}/?topup=cancel",
        metadata={"workspace_id": workspace_id, "user_id": user_id, "type": "topup"},
    )
    return session.url


def create_addon_checkout(user_email: str, workspace_id: str, addon_type: str) -> str:
    """Create a Stripe Checkout session for an add-on subscription."""
    customer_id = get_or_create_customer(user_email, workspace_id)

    price_map = {"api_access": STRIPE_API_ADDON_PRICE_ID}
    price_id = price_map.get(addon_type)
    if not price_id:
        raise ValueError(f"No Stripe price for add-on: {addon_type}")

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{BASE_URL}/?addon=success",
        cancel_url=f"{BASE_URL}/?addon=cancel",
        metadata={"workspace_id": workspace_id, "addon_type": addon_type},
    )
    return session.url


# ---------------------------------------------------------------------------
# Subscription management
# ---------------------------------------------------------------------------

def cancel_subscription(workspace_id: str) -> bool:
    """Cancel subscription at period end."""
    sub = queries.get_subscription(workspace_id)
    if not sub or not sub.stripe_subscription_id:
        return False

    stripe.Subscription.modify(
        sub.stripe_subscription_id,
        cancel_at_period_end=True,
    )
    return True


def get_subscription_status(workspace_id: str) -> Optional[dict]:
    """Get current subscription details from Stripe."""
    sub = queries.get_subscription(workspace_id)
    if not sub or not sub.stripe_subscription_id:
        return {"tier": "free", "status": "active"}

    try:
        stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id)
        return {
            "tier": sub.tier,
            "status": stripe_sub.status,
            "cancel_at_period_end": stripe_sub.cancel_at_period_end,
            "current_period_end": stripe_sub.current_period_end,
        }
    except stripe.StripeError:
        return {"tier": sub.tier, "status": sub.status}


# ---------------------------------------------------------------------------
# Webhook handling
# ---------------------------------------------------------------------------

def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """Process a Stripe webhook event. Returns {"status": "ok"} or error."""
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError) as e:
        return {"status": "error", "message": str(e)}

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data)
    elif event_type == "invoice.paid":
        _handle_invoice_paid(data)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data)

    return {"status": "ok"}


def _handle_checkout_completed(session: dict):
    """Handle successful checkout — activate subscription or process top-up."""
    metadata = session.get("metadata", {})
    workspace_id = metadata.get("workspace_id")
    if not workspace_id:
        return

    if metadata.get("type") == "topup":
        # Credit top-up
        user_id = metadata.get("user_id", "")
        from config.settings import TOPUP_CREDITS, TOPUP_PRICE_CENTS
        credit_service.add_credits(
            workspace_id=workspace_id,
            user_id=user_id,
            amount=TOPUP_CREDITS,
            reason="Credit top-up purchase",
            reference_id=session.get("id"),
        )
        queries.create_credit_purchase(
            workspace_id=workspace_id,
            purchased_by=user_id,
            credits_purchased=TOPUP_CREDITS,
            amount_paid_cents=TOPUP_PRICE_CENTS,
            stripe_payment_id=session.get("payment_intent"),
        )
    elif metadata.get("addon_type"):
        # Add-on activation
        queries.create_add_on(
            workspace_id=workspace_id,
            add_on_type=metadata["addon_type"],
            stripe_subscription_id=session.get("subscription"),
        )
    else:
        # Subscription activation
        tier = metadata.get("tier", "pro")
        tier_config = TIERS.get(tier, TIERS["pro"])
        queries.update_workspace(workspace_id, tier=tier)

        # Update or create subscription record
        sub = queries.get_subscription(workspace_id)
        if sub:
            queries.update_subscription(
                sub.id, tier=tier,
                stripe_subscription_id=session.get("subscription"),
                monthly_credit_allowance=tier_config["monthly_credits"],
                status="active",
            )
        else:
            queries.create_subscription(
                workspace_id=workspace_id,
                tier=tier,
                monthly_credit_allowance=tier_config["monthly_credits"],
                stripe_subscription_id=session.get("subscription"),
            )

        # Grant credits
        ws = queries.get_workspace_by_id(workspace_id)
        credit_service.reset_monthly_credits(workspace_id, ws.owner_id if ws else "", tier)


def _handle_invoice_paid(invoice: dict):
    """Handle monthly renewal — reset credits."""
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return

    # Find workspace by subscription
    # This requires a lookup — for now iterate (would use index in production)
    # Simplified: use customer metadata
    customer_id = invoice.get("customer")
    if customer_id:
        from db.database import get_db
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, owner_id, tier FROM workspaces WHERE stripe_customer_id = ?",
                (customer_id,),
            ).fetchone()
        if row:
            workspace_id = row["id"]
            tier = row["tier"]
            credit_service.reset_monthly_credits(workspace_id, row["owner_id"], tier)


def _handle_subscription_updated(subscription: dict):
    """Handle subscription tier change."""
    pass  # Tier changes are handled via checkout.session.completed


def _handle_subscription_deleted(subscription: dict):
    """Handle subscription cancellation — downgrade to free."""
    customer_id = subscription.get("customer")
    if customer_id:
        from db.database import get_db
        with get_db() as conn:
            row = conn.execute(
                "SELECT id FROM workspaces WHERE stripe_customer_id = ?",
                (customer_id,),
            ).fetchone()
        if row:
            queries.update_workspace(row["id"], tier="free")
