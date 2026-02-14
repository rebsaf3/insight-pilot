"""Workspace management — creation, invitation, role enforcement, trials."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from config.settings import TIERS, TRIAL_DAYS, TRIAL_TIER, TRIAL_CREDITS
from db import queries
from db.models import Workspace, WorkspaceMember


def create_personal_workspace(user_id: str, display_name: str) -> str:
    """Create the default personal workspace for a new user.
    Called during registration. Also creates the free subscription and initial credits."""
    ws_name = f"{display_name}'s Workspace"
    ws_id = queries.create_workspace(name=ws_name, owner_id=user_id, tier="free")

    # Create free subscription
    tier_config = TIERS["free"]
    queries.create_subscription(
        workspace_id=ws_id,
        tier="free",
        monthly_credit_allowance=tier_config["monthly_credits"],
    )

    # Grant initial credits
    queries.add_credit_entry(
        workspace_id=ws_id,
        user_id=user_id,
        change_amount=tier_config["monthly_credits"],
        balance_after=tier_config["monthly_credits"],
        reason="Initial free tier credits",
    )

    # Create default branding
    queries.upsert_branding(ws_id)

    return ws_id


def create_shared_workspace(owner_id: str, name: str, description: str = "") -> str:
    """Create a new shared workspace."""
    ws_id = queries.create_workspace(name=name, owner_id=owner_id, tier="free", description=description)

    tier_config = TIERS["free"]
    queries.create_subscription(
        workspace_id=ws_id,
        tier="free",
        monthly_credit_allowance=tier_config["monthly_credits"],
    )

    queries.add_credit_entry(
        workspace_id=ws_id,
        user_id=owner_id,
        change_amount=tier_config["monthly_credits"],
        balance_after=tier_config["monthly_credits"],
        reason="Initial free tier credits",
    )

    queries.upsert_branding(ws_id)

    return ws_id


def get_user_workspaces(user_id: str) -> list[Workspace]:
    """Get all workspaces a user belongs to."""
    return queries.get_workspaces_for_user(user_id)


def get_workspace_tier_config(workspace: Workspace) -> dict:
    """Get the tier configuration for a workspace."""
    return TIERS.get(workspace.tier, TIERS["free"])


def can_add_member(workspace_id: str) -> tuple[bool, str]:
    """Check if the workspace can add another member based on tier limits."""
    ws = queries.get_workspace_by_id(workspace_id)
    if not ws:
        return False, "Workspace not found."

    tier_config = TIERS.get(ws.tier, TIERS["free"])
    max_members = tier_config["max_members"]
    if max_members == -1:
        return True, ""

    current_count = queries.count_workspace_members(workspace_id)
    if current_count >= max_members:
        return False, f"Your {tier_config['name']} plan allows up to {max_members} members. Upgrade to add more."

    return True, ""


def invite_member(workspace_id: str, email: str, role: str, invited_by: str) -> tuple[bool, str]:
    """Create an invitation for a new member."""
    import secrets
    from datetime import datetime, timedelta, timezone

    can_add, msg = can_add_member(workspace_id)
    if not can_add:
        return False, msg

    if role not in ("admin", "member", "viewer"):
        return False, "Invalid role."

    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    queries.create_invitation(
        workspace_id=workspace_id,
        email=email.strip().lower(),
        role=role,
        invited_by=invited_by,
        token=token,
        expires_at=expires_at,
    )

    return True, token


def accept_invitation(token: str, user_id: str) -> tuple[bool, str]:
    """Accept a workspace invitation."""
    invitation = queries.get_invitation_by_token(token)
    if not invitation:
        return False, "Invalid or expired invitation."

    # Check if already a member
    existing_role = queries.get_member_role(invitation.workspace_id, user_id)
    if existing_role:
        queries.accept_invitation(invitation.id)
        return True, "You're already a member of this workspace."

    queries.add_workspace_member(
        workspace_id=invitation.workspace_id,
        user_id=user_id,
        role=invitation.role,
        invited_by=invitation.invited_by,
    )
    queries.accept_invitation(invitation.id)

    return True, "Welcome to the workspace!"


# =========================================================================
# Trial Management
# =========================================================================

def start_trial(workspace_id: str, user_id: str) -> bool:
    """Activate a 7-day Pro trial for a workspace.

    Sets the workspace tier to Pro, grants trial credits, and records
    ``trial_ends_at``.  Called once during registration.
    """
    trial_end = (datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # Upgrade tier and set trial expiry
    queries.update_workspace(workspace_id, tier=TRIAL_TIER, trial_ends_at=trial_end)

    # Update the subscription to match the trial tier
    sub = queries.get_subscription(workspace_id)
    if sub:
        tier_cfg = TIERS[TRIAL_TIER]
        queries.update_subscription(
            sub.id, tier=TRIAL_TIER,
            monthly_credit_allowance=tier_cfg["monthly_credits"],
        )

    # Grant trial credits
    current_balance = queries.get_credit_balance(workspace_id)
    queries.add_credit_entry(
        workspace_id=workspace_id,
        user_id=user_id,
        change_amount=TRIAL_CREDITS,
        balance_after=current_balance + TRIAL_CREDITS,
        reason="Pro trial activated — 7-day trial credits",
    )

    return True


def check_trial_status(workspace_id: str) -> str:
    """Return the trial status for a workspace.

    Returns one of:
    - ``"active"`` — trial is running, trial_ends_at is in the future
    - ``"expired"`` — trial_ends_at has passed
    - ``"none"`` — workspace was never on a trial
    """
    ws = queries.get_workspace_by_id(workspace_id)
    if not ws or not ws.trial_ends_at:
        return "none"
    try:
        ends = datetime.fromisoformat(ws.trial_ends_at)
        if ends.tzinfo is None:
            ends = ends.replace(tzinfo=timezone.utc)
        if ends > datetime.now(timezone.utc):
            return "active"
        return "expired"
    except (ValueError, TypeError):
        return "none"


def get_trial_days_remaining(workspace_id: str) -> int:
    """Return the number of full days remaining in the trial, or 0."""
    ws = queries.get_workspace_by_id(workspace_id)
    if not ws or not ws.trial_ends_at:
        return 0
    try:
        ends = datetime.fromisoformat(ws.trial_ends_at)
        if ends.tzinfo is None:
            ends = ends.replace(tzinfo=timezone.utc)
        delta = ends - datetime.now(timezone.utc)
        return max(0, delta.days)
    except (ValueError, TypeError):
        return 0


def expire_trial(workspace_id: str) -> bool:
    """Downgrade a workspace whose trial has ended back to the free tier.

    Called during the app startup check (``app.py``) so expiry is enforced
    on every page load.
    """
    queries.update_workspace(workspace_id, tier="free")

    sub = queries.get_subscription(workspace_id)
    if sub:
        free_cfg = TIERS["free"]
        queries.update_subscription(
            sub.id, tier="free",
            monthly_credit_allowance=free_cfg["monthly_credits"],
        )
    return True
