"""Credit management service — balance, deductions, limits, usage tracking."""

import math
from typing import Optional

from config.settings import TIERS, TOKENS_PER_CREDIT
from db import queries


def get_balance(workspace_id: str) -> int:
    """Return current credit balance for a workspace."""
    return queries.get_credit_balance(workspace_id)


def check_sufficient_credits(workspace_id: str, estimated_cost: int = 5) -> tuple[bool, int]:
    """Check if workspace has enough credits. Returns (has_enough, current_balance)."""
    balance = get_balance(workspace_id)
    return balance >= estimated_cost, balance


def deduct_credits(workspace_id: str, user_id: str, amount: int,
                   reason: str, reference_id: str = None) -> int:
    """Deduct credits from workspace. Returns new balance."""
    current = get_balance(workspace_id)
    new_balance = max(0, current - amount)
    queries.add_credit_entry(
        workspace_id=workspace_id,
        user_id=user_id,
        change_amount=-amount,
        balance_after=new_balance,
        reason=reason,
        reference_id=reference_id,
    )
    return new_balance


def add_credits(workspace_id: str, user_id: str, amount: int,
                reason: str, reference_id: str = None) -> int:
    """Add credits to workspace. Returns new balance."""
    current = get_balance(workspace_id)
    new_balance = current + amount
    queries.add_credit_entry(
        workspace_id=workspace_id,
        user_id=user_id,
        change_amount=amount,
        balance_after=new_balance,
        reason=reason,
        reference_id=reference_id,
    )
    return new_balance


def calculate_credit_cost(tokens_used: int) -> int:
    """Convert token count to credits. Minimum 1 credit."""
    return max(1, math.ceil(tokens_used / TOKENS_PER_CREDIT))


def check_upload_allowed(user_id: str, workspace_id: str) -> tuple[bool, str]:
    """Check if user can upload based on tier daily limits."""
    ws = queries.get_workspace_by_id(workspace_id)
    if not ws:
        return False, "Workspace not found."

    tier_config = TIERS.get(ws.tier, TIERS["free"])
    max_uploads = tier_config["uploads_per_day"]
    if max_uploads == -1:
        return True, ""

    today_count = queries.count_uploads_today(user_id)
    if today_count >= max_uploads:
        return False, f"Daily upload limit reached ({max_uploads}/day on {tier_config['name']}). Upgrade for more."

    return True, ""


def check_file_size_allowed(workspace_id: str, file_size_bytes: int) -> tuple[bool, str]:
    """Check if file size is within tier limits."""
    ws = queries.get_workspace_by_id(workspace_id)
    if not ws:
        return False, "Workspace not found."

    tier_config = TIERS.get(ws.tier, TIERS["free"])
    max_mb = tier_config["max_file_size_mb"]
    file_mb = file_size_bytes / (1024 * 1024)
    if file_mb > max_mb:
        return False, f"File too large ({file_mb:.1f} MB). {tier_config['name']} plan limit: {max_mb} MB."

    return True, ""


def check_dashboard_limit(workspace_id: str) -> tuple[bool, str]:
    """Check if workspace can create another dashboard."""
    ws = queries.get_workspace_by_id(workspace_id)
    if not ws:
        return False, "Workspace not found."

    tier_config = TIERS.get(ws.tier, TIERS["free"])
    max_dashboards = tier_config["max_dashboards"]
    if max_dashboards == -1:
        return True, ""

    current_count = queries.count_dashboards_in_workspace(workspace_id)
    if current_count >= max_dashboards:
        return False, f"Dashboard limit reached ({max_dashboards} on {tier_config['name']}). Upgrade for more."

    return True, ""


def check_revisions_allowed(workspace_id: str) -> tuple[bool, str]:
    """Check if revisions are allowed for the workspace tier."""
    ws = queries.get_workspace_by_id(workspace_id)
    if not ws:
        return False, "Workspace not found."

    tier_config = TIERS.get(ws.tier, TIERS["free"])
    max_revisions = tier_config["max_revisions_per_report"]
    if max_revisions == 0:
        return False, f"Revisions are not available on the {tier_config['name']} plan. Upgrade to Pro."

    return True, ""


def check_export_allowed(workspace_id: str) -> tuple[bool, str]:
    """Check if export is allowed for the workspace tier."""
    ws = queries.get_workspace_by_id(workspace_id)
    if not ws:
        return False, "Workspace not found."

    tier_config = TIERS.get(ws.tier, TIERS["free"])
    if not tier_config["export_enabled"]:
        return False, f"Export is not available on the {tier_config['name']} plan. Upgrade to Pro."

    return True, ""


def get_usage_summary(workspace_id: str, user_id: str) -> dict:
    """Get usage summary for display in sidebar/billing."""
    balance = get_balance(workspace_id)
    ws = queries.get_workspace_by_id(workspace_id)
    tier_config = TIERS.get(ws.tier if ws else "free", TIERS["free"])

    return {
        "credits_remaining": balance,
        "monthly_allowance": tier_config["monthly_credits"],
        "uploads_today": queries.count_uploads_today(user_id),
        "uploads_limit": tier_config["uploads_per_day"],
        "dashboards_count": queries.count_dashboards_in_workspace(workspace_id),
        "dashboards_limit": tier_config["max_dashboards"],
        "tier": ws.tier if ws else "free",
        "tier_name": tier_config["name"],
    }


def reset_monthly_credits(workspace_id: str, user_id: str, tier: str) -> None:
    """Reset credits to monthly allowance on subscription renewal."""
    tier_config = TIERS.get(tier, TIERS["free"])
    allowance = tier_config["monthly_credits"]

    # Set balance to the monthly allowance (not add)
    queries.add_credit_entry(
        workspace_id=workspace_id,
        user_id=user_id,
        change_amount=allowance,
        balance_after=allowance,
        reason=f"Monthly credit reset ({tier_config['name']})",
    )
