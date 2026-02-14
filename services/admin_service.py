"""Admin service — aggregated metrics, admin operations, and superadmin bootstrap."""

from config.settings import TIERS, ADMIN_EMAIL
from db import queries


def ensure_superadmin() -> None:
    """Ensure the ADMIN_EMAIL user (if set) has is_superadmin=True.
    Called during app startup. No-op if the user hasn't registered yet."""
    if ADMIN_EMAIL:
        queries.set_superadmin_by_email(ADMIN_EMAIL)


def get_dashboard_kpis() -> dict:
    """Return KPIs for the admin dashboard overview."""
    return {
        "total_users": queries.count_all_users(),
        "total_workspaces": queries.count_all_workspaces(),
        "subscriptions_by_tier": queries.count_subscriptions_by_tier(),
        "total_credits_consumed": queries.get_total_credits_consumed(),
        "total_api_calls": queries.get_total_api_calls(),
        "total_revenue_cents": queries.get_total_revenue_cents(),
    }


def adjust_workspace_credits(workspace_id: str, admin_user_id: str,
                              amount: int, reason: str) -> int:
    """Admin adjustment of workspace credits. Positive=add, negative=deduct."""
    from services.credit_service import add_credits, deduct_credits
    if amount > 0:
        new_balance = add_credits(workspace_id, admin_user_id, amount,
                                  f"Admin adjustment: {reason}")
    else:
        new_balance = deduct_credits(workspace_id, admin_user_id, abs(amount),
                                     f"Admin adjustment: {reason}")
    queries.create_audit_log(
        user_id=admin_user_id,
        action="adjust_credits",
        entity_type="workspace",
        entity_id=workspace_id,
        details={"amount": amount, "reason": reason, "new_balance": new_balance},
    )
    return new_balance


def change_workspace_tier(workspace_id: str, new_tier: str, admin_user_id: str) -> bool:
    """Admin change of workspace tier."""
    if new_tier not in TIERS:
        return False
    queries.update_workspace(workspace_id, tier=new_tier)
    queries.create_audit_log(
        user_id=admin_user_id,
        action="change_tier",
        entity_type="workspace",
        entity_id=workspace_id,
        details={"new_tier": new_tier},
    )
    return True


def toggle_superadmin(user_id: str, is_superadmin: bool, admin_user_id: str) -> bool:
    """Toggle superadmin status for a user."""
    queries.set_user_superadmin(user_id, is_superadmin)
    queries.create_audit_log(
        user_id=admin_user_id,
        action="toggle_superadmin",
        entity_type="user",
        entity_id=user_id,
        details={"is_superadmin": is_superadmin},
    )
    return True
