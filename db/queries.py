"""All database query functions. Every function that accesses user/workspace
data requires workspace_id or user_id to enforce multi-tenancy."""

import json
import uuid
from typing import Optional

from db.database import get_db
from db.models import (
    User, UserSession, Workspace, WorkspaceMember, WorkspaceInvitation,
    Project, UploadedFile, Dashboard, Chart, CreditLedgerEntry,
    Subscription, CreditPurchase, AddOn, WorkspaceBranding, ApiKey,
    PromptHistoryEntry, row_to_model, rows_to_models,
)


def _new_id() -> str:
    return uuid.uuid4().hex


# =========================================================================
# Users
# =========================================================================

def create_user(email: str, password_hash: str, display_name: str) -> str:
    uid = _new_id()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, display_name) VALUES (?, ?, ?, ?)",
            (uid, email, password_hash, display_name),
        )
    return uid


def get_user_by_id(user_id: str) -> Optional[User]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return row_to_model(row, User)


def get_user_by_email(email: str) -> Optional[User]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return row_to_model(row, User)


def update_user(user_id: str, **kwargs) -> bool:
    if not kwargs:
        return False
    kwargs["updated_at"] = "datetime('now')"
    sets = []
    vals = []
    for k, v in kwargs.items():
        if v == "datetime('now')":
            sets.append(f"{k} = datetime('now')")
        else:
            sets.append(f"{k} = ?")
            vals.append(v)
    vals.append(user_id)
    sql = f"UPDATE users SET {', '.join(sets)} WHERE id = ?"
    with get_db() as conn:
        conn.execute(sql, tuple(vals))
    return True


def delete_user(user_id: str) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return True


# =========================================================================
# Email Verification Codes
# =========================================================================

def create_verification_code(user_id: str, code: str, purpose: str, expires_at: str) -> str:
    vid = _new_id()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO email_verification_codes (id, user_id, code, purpose, expires_at) VALUES (?, ?, ?, ?, ?)",
            (vid, user_id, code, purpose, expires_at),
        )
    return vid


def get_valid_verification_code(user_id: str, code: str, purpose: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            """SELECT * FROM email_verification_codes
               WHERE user_id = ? AND code = ? AND purpose = ?
               AND used_at IS NULL AND expires_at > datetime('now')
               ORDER BY created_at DESC LIMIT 1""",
            (user_id, code, purpose),
        ).fetchone()
    return dict(row) if row else None


def mark_verification_code_used(code_id: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE email_verification_codes SET used_at = datetime('now') WHERE id = ?",
            (code_id,),
        )


def count_recent_verification_codes(user_id: str, purpose: str, minutes: int = 15) -> int:
    with get_db() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as cnt FROM email_verification_codes
               WHERE user_id = ? AND purpose = ?
               AND created_at > datetime('now', ? || ' minutes')""",
            (user_id, purpose, f"-{minutes}"),
        ).fetchone()
    return row["cnt"]


# =========================================================================
# User Sessions
# =========================================================================

def create_session(user_id: str, session_token: str, expires_at: str,
                   ip_address: str = None, user_agent: str = None) -> str:
    sid = _new_id()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO user_sessions (id, user_id, session_token, ip_address, user_agent, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sid, user_id, session_token, ip_address, user_agent, expires_at),
        )
    return sid


def get_session_by_token(token: str) -> Optional[UserSession]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_sessions WHERE session_token = ? AND expires_at > datetime('now')",
            (token,),
        ).fetchone()
    return row_to_model(row, UserSession)


def get_user_sessions(user_id: str) -> list[UserSession]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM user_sessions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return rows_to_models(rows, UserSession)


def delete_session(session_id: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM user_sessions WHERE id = ?", (session_id,))


def delete_session_by_token(token: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM user_sessions WHERE session_token = ?", (token,))


def delete_all_user_sessions(user_id: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))


# =========================================================================
# Backup Codes
# =========================================================================

def create_backup_codes(user_id: str, code_hashes: list[str]) -> None:
    with get_db() as conn:
        # Remove old codes first
        conn.execute("DELETE FROM backup_codes WHERE user_id = ?", (user_id,))
        for h in code_hashes:
            conn.execute(
                "INSERT INTO backup_codes (id, user_id, code_hash) VALUES (?, ?, ?)",
                (_new_id(), user_id, h),
            )


def get_unused_backup_code(user_id: str, code_hash: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM backup_codes WHERE user_id = ? AND code_hash = ? AND used_at IS NULL",
            (user_id, code_hash),
        ).fetchone()
    return dict(row) if row else None


def mark_backup_code_used(code_id: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE backup_codes SET used_at = datetime('now') WHERE id = ?",
            (code_id,),
        )


# =========================================================================
# Workspaces
# =========================================================================

def create_workspace(name: str, owner_id: str, tier: str = "free", description: str = "") -> str:
    wid = _new_id()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO workspaces (id, name, description, owner_id, tier) VALUES (?, ?, ?, ?, ?)",
            (wid, name, description, owner_id, tier),
        )
        # Owner is automatically a member with 'owner' role
        conn.execute(
            "INSERT INTO workspace_members (id, workspace_id, user_id, role) VALUES (?, ?, ?, 'owner')",
            (_new_id(), wid, owner_id),
        )
    return wid


def get_workspace_by_id(workspace_id: str) -> Optional[Workspace]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
    return row_to_model(row, Workspace)


def get_workspaces_for_user(user_id: str) -> list[Workspace]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT w.* FROM workspaces w
               JOIN workspace_members wm ON w.id = wm.workspace_id
               WHERE wm.user_id = ? ORDER BY w.created_at""",
            (user_id,),
        ).fetchall()
    return rows_to_models(rows, Workspace)


def update_workspace(workspace_id: str, **kwargs) -> bool:
    if not kwargs:
        return False
    kwargs["updated_at"] = "datetime('now')"
    sets = []
    vals = []
    for k, v in kwargs.items():
        if v == "datetime('now')":
            sets.append(f"{k} = datetime('now')")
        else:
            sets.append(f"{k} = ?")
            vals.append(v if not isinstance(v, dict) else json.dumps(v))
    vals.append(workspace_id)
    sql = f"UPDATE workspaces SET {', '.join(sets)} WHERE id = ?"
    with get_db() as conn:
        conn.execute(sql, tuple(vals))
    return True


def delete_workspace(workspace_id: str) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM workspaces WHERE id = ?", (workspace_id,))
    return True


# =========================================================================
# Workspace Members
# =========================================================================

def add_workspace_member(workspace_id: str, user_id: str, role: str, invited_by: str = None) -> str:
    mid = _new_id()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO workspace_members (id, workspace_id, user_id, role, invited_by) VALUES (?, ?, ?, ?, ?)",
            (mid, workspace_id, user_id, role, invited_by),
        )
    return mid


def get_workspace_members(workspace_id: str) -> list[WorkspaceMember]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM workspace_members WHERE workspace_id = ? ORDER BY joined_at",
            (workspace_id,),
        ).fetchall()
    return rows_to_models(rows, WorkspaceMember)


def get_member_role(workspace_id: str, user_id: str) -> Optional[str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT role FROM workspace_members WHERE workspace_id = ? AND user_id = ?",
            (workspace_id, user_id),
        ).fetchone()
    return row["role"] if row else None


def update_member_role(workspace_id: str, user_id: str, new_role: str) -> bool:
    with get_db() as conn:
        conn.execute(
            "UPDATE workspace_members SET role = ? WHERE workspace_id = ? AND user_id = ?",
            (new_role, workspace_id, user_id),
        )
    return True


def remove_workspace_member(workspace_id: str, user_id: str) -> bool:
    with get_db() as conn:
        conn.execute(
            "DELETE FROM workspace_members WHERE workspace_id = ? AND user_id = ?",
            (workspace_id, user_id),
        )
    return True


def count_workspace_members(workspace_id: str) -> int:
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM workspace_members WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
    return row["cnt"]


# =========================================================================
# Workspace Invitations
# =========================================================================

def create_invitation(workspace_id: str, email: str, role: str, invited_by: str, token: str, expires_at: str) -> str:
    iid = _new_id()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO workspace_invitations (id, workspace_id, email, role, invited_by, token, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (iid, workspace_id, email, role, invited_by, token, expires_at),
        )
    return iid


def get_invitation_by_token(token: str) -> Optional[WorkspaceInvitation]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM workspace_invitations WHERE token = ? AND status = 'pending' AND expires_at > datetime('now')",
            (token,),
        ).fetchone()
    return row_to_model(row, WorkspaceInvitation)


def get_pending_invitations(workspace_id: str) -> list[WorkspaceInvitation]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM workspace_invitations WHERE workspace_id = ? AND status = 'pending' ORDER BY created_at DESC",
            (workspace_id,),
        ).fetchall()
    return rows_to_models(rows, WorkspaceInvitation)


def accept_invitation(invitation_id: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE workspace_invitations SET status = 'accepted' WHERE id = ?",
            (invitation_id,),
        )


def revoke_invitation(invitation_id: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE workspace_invitations SET status = 'expired' WHERE id = ?",
            (invitation_id,),
        )


# =========================================================================
# Projects
# =========================================================================

def create_project(workspace_id: str, created_by: str, name: str, description: str = "") -> str:
    pid = _new_id()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO projects (id, workspace_id, created_by, name, description) VALUES (?, ?, ?, ?, ?)",
            (pid, workspace_id, created_by, name, description),
        )
    return pid


def get_projects_for_workspace(workspace_id: str) -> list[Project]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM projects WHERE workspace_id = ? ORDER BY created_at DESC",
            (workspace_id,),
        ).fetchall()
    return rows_to_models(rows, Project)


def get_project_by_id(project_id: str, workspace_id: str) -> Optional[Project]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ? AND workspace_id = ?",
            (project_id, workspace_id),
        ).fetchone()
    return row_to_model(row, Project)


def update_project(project_id: str, workspace_id: str, **kwargs) -> bool:
    if not kwargs:
        return False
    kwargs["updated_at"] = "datetime('now')"
    sets = []
    vals = []
    for k, v in kwargs.items():
        if v == "datetime('now')":
            sets.append(f"{k} = datetime('now')")
        else:
            sets.append(f"{k} = ?")
            vals.append(v)
    vals.extend([project_id, workspace_id])
    sql = f"UPDATE projects SET {', '.join(sets)} WHERE id = ? AND workspace_id = ?"
    with get_db() as conn:
        conn.execute(sql, tuple(vals))
    return True


def delete_project(project_id: str, workspace_id: str) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM projects WHERE id = ? AND workspace_id = ?", (project_id, workspace_id))
    return True


# =========================================================================
# Uploaded Files
# =========================================================================

def create_uploaded_file(project_id: str, uploaded_by: str, original_filename: str,
                         stored_filename: str, file_path: str, file_format: str,
                         file_size_bytes: int) -> str:
    fid = _new_id()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO uploaded_files
               (id, project_id, uploaded_by, original_filename, stored_filename, file_path, file_format, file_size_bytes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (fid, project_id, uploaded_by, original_filename, stored_filename, file_path, file_format, file_size_bytes),
        )
    return fid


def get_files_for_project(project_id: str) -> list[UploadedFile]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM uploaded_files WHERE project_id = ? ORDER BY uploaded_at DESC",
            (project_id,),
        ).fetchall()
    return rows_to_models(rows, UploadedFile)


def get_file_by_id(file_id: str) -> Optional[UploadedFile]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM uploaded_files WHERE id = ?", (file_id,)).fetchone()
    return row_to_model(row, UploadedFile)


def update_file_profile(file_id: str, row_count: int, column_count: int,
                         column_names: list[str], data_profile: dict) -> bool:
    with get_db() as conn:
        conn.execute(
            """UPDATE uploaded_files SET row_count = ?, column_count = ?,
               column_names = ?, data_profile = ? WHERE id = ?""",
            (row_count, column_count, json.dumps(column_names), json.dumps(data_profile), file_id),
        )
    return True


def delete_file(file_id: str) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM uploaded_files WHERE id = ?", (file_id,))
    return True


def count_uploads_today(user_id: str) -> int:
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM uploaded_files WHERE uploaded_by = ? AND date(uploaded_at) = date('now')",
            (user_id,),
        ).fetchone()
    return row["cnt"]


# =========================================================================
# Dashboards
# =========================================================================

def create_dashboard(project_id: str, created_by: str, name: str, description: str = "") -> str:
    did = _new_id()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO dashboards (id, project_id, created_by, name, description) VALUES (?, ?, ?, ?, ?)",
            (did, project_id, created_by, name, description),
        )
    return did


def get_dashboards_for_project(project_id: str) -> list[Dashboard]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM dashboards WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
    return rows_to_models(rows, Dashboard)


def get_dashboard_by_id(dashboard_id: str) -> Optional[Dashboard]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM dashboards WHERE id = ?", (dashboard_id,)).fetchone()
    return row_to_model(row, Dashboard)


def update_dashboard(dashboard_id: str, **kwargs) -> bool:
    if not kwargs:
        return False
    kwargs["updated_at"] = "datetime('now')"
    sets = []
    vals = []
    for k, v in kwargs.items():
        if v == "datetime('now')":
            sets.append(f"{k} = datetime('now')")
        else:
            sets.append(f"{k} = ?")
            vals.append(v if not isinstance(v, (dict, list)) else json.dumps(v))
    vals.append(dashboard_id)
    sql = f"UPDATE dashboards SET {', '.join(sets)} WHERE id = ?"
    with get_db() as conn:
        conn.execute(sql, tuple(vals))
    return True


def delete_dashboard(dashboard_id: str) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM dashboards WHERE id = ?", (dashboard_id,))
    return True


def count_dashboards_in_workspace(workspace_id: str) -> int:
    with get_db() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as cnt FROM dashboards d
               JOIN projects p ON d.project_id = p.id
               WHERE p.workspace_id = ?""",
            (workspace_id,),
        ).fetchone()
    return row["cnt"]


# =========================================================================
# Charts
# =========================================================================

def create_chart(dashboard_id: str, file_id: str, title: str, user_prompt: str,
                 generated_code: str, created_by: str, chart_type: str = None,
                 plotly_json: str = None, position_index: int = 0) -> str:
    cid = _new_id()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO charts
               (id, dashboard_id, file_id, title, chart_type, user_prompt, generated_code, plotly_json, position_index, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cid, dashboard_id, file_id, title, chart_type, user_prompt, generated_code, plotly_json, position_index, created_by),
        )
    return cid


def get_charts_for_dashboard(dashboard_id: str) -> list[Chart]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM charts WHERE dashboard_id = ? ORDER BY position_index",
            (dashboard_id,),
        ).fetchall()
    return rows_to_models(rows, Chart)


def get_chart_by_id(chart_id: str) -> Optional[Chart]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM charts WHERE id = ?", (chart_id,)).fetchone()
    return row_to_model(row, Chart)


def update_chart(chart_id: str, **kwargs) -> bool:
    if not kwargs:
        return False
    kwargs["updated_at"] = "datetime('now')"
    sets = []
    vals = []
    for k, v in kwargs.items():
        if v == "datetime('now')":
            sets.append(f"{k} = datetime('now')")
        else:
            sets.append(f"{k} = ?")
            vals.append(v if not isinstance(v, (dict, list)) else json.dumps(v))
    vals.append(chart_id)
    sql = f"UPDATE charts SET {', '.join(sets)} WHERE id = ?"
    with get_db() as conn:
        conn.execute(sql, tuple(vals))
    return True


def delete_chart(chart_id: str) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM charts WHERE id = ?", (chart_id,))
    return True


def reorder_charts(dashboard_id: str, chart_id_order: list[str]) -> bool:
    with get_db() as conn:
        for idx, cid in enumerate(chart_id_order):
            conn.execute(
                "UPDATE charts SET position_index = ?, updated_at = datetime('now') WHERE id = ? AND dashboard_id = ?",
                (idx, cid, dashboard_id),
            )
    return True


# =========================================================================
# Credit Ledger
# =========================================================================

def add_credit_entry(workspace_id: str, user_id: str, change_amount: int,
                     balance_after: int, reason: str, reference_id: str = None) -> str:
    eid = _new_id()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO credit_ledger (id, workspace_id, user_id, change_amount, balance_after, reason, reference_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (eid, workspace_id, user_id, change_amount, balance_after, reason, reference_id),
        )
    return eid


def get_credit_balance(workspace_id: str) -> int:
    with get_db() as conn:
        row = conn.execute(
            "SELECT balance_after FROM credit_ledger WHERE workspace_id = ? ORDER BY created_at DESC LIMIT 1",
            (workspace_id,),
        ).fetchone()
    return row["balance_after"] if row else 0


def get_credit_history(workspace_id: str, limit: int = 50) -> list[CreditLedgerEntry]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM credit_ledger WHERE workspace_id = ? ORDER BY created_at DESC LIMIT ?",
            (workspace_id, limit),
        ).fetchall()
    return rows_to_models(rows, CreditLedgerEntry)


# =========================================================================
# Subscriptions
# =========================================================================

def create_subscription(workspace_id: str, tier: str, monthly_credit_allowance: int,
                         stripe_subscription_id: str = None) -> str:
    sid = _new_id()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO subscriptions (id, workspace_id, tier, stripe_subscription_id, monthly_credit_allowance)
               VALUES (?, ?, ?, ?, ?)""",
            (sid, workspace_id, tier, stripe_subscription_id, monthly_credit_allowance),
        )
    return sid


def get_subscription(workspace_id: str) -> Optional[Subscription]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE workspace_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1",
            (workspace_id,),
        ).fetchone()
    return row_to_model(row, Subscription)


def update_subscription(subscription_id: str, **kwargs) -> bool:
    if not kwargs:
        return False
    kwargs["updated_at"] = "datetime('now')"
    sets = []
    vals = []
    for k, v in kwargs.items():
        if v == "datetime('now')":
            sets.append(f"{k} = datetime('now')")
        else:
            sets.append(f"{k} = ?")
            vals.append(v)
    vals.append(subscription_id)
    sql = f"UPDATE subscriptions SET {', '.join(sets)} WHERE id = ?"
    with get_db() as conn:
        conn.execute(sql, tuple(vals))
    return True


# =========================================================================
# Credit Purchases
# =========================================================================

def create_credit_purchase(workspace_id: str, purchased_by: str, credits_purchased: int,
                            amount_paid_cents: int, stripe_payment_id: str = None) -> str:
    pid = _new_id()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO credit_purchases (id, workspace_id, purchased_by, stripe_payment_id, credits_purchased, amount_paid_cents)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (pid, workspace_id, purchased_by, stripe_payment_id, credits_purchased, amount_paid_cents),
        )
    return pid


# =========================================================================
# Add-Ons
# =========================================================================

def create_add_on(workspace_id: str, add_on_type: str, stripe_subscription_id: str = None) -> str:
    aid = _new_id()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO add_ons (id, workspace_id, add_on_type, stripe_subscription_id) VALUES (?, ?, ?, ?)",
            (aid, workspace_id, add_on_type, stripe_subscription_id),
        )
    return aid


def get_add_on(workspace_id: str, add_on_type: str) -> Optional[AddOn]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM add_ons WHERE workspace_id = ? AND add_on_type = ? AND status = 'active'",
            (workspace_id, add_on_type),
        ).fetchone()
    return row_to_model(row, AddOn)


def update_add_on(add_on_id: str, **kwargs) -> bool:
    if not kwargs:
        return False
    kwargs["updated_at"] = "datetime('now')"
    sets = []
    vals = []
    for k, v in kwargs.items():
        if v == "datetime('now')":
            sets.append(f"{k} = datetime('now')")
        else:
            sets.append(f"{k} = ?")
            vals.append(v)
    vals.append(add_on_id)
    sql = f"UPDATE add_ons SET {', '.join(sets)} WHERE id = ?"
    with get_db() as conn:
        conn.execute(sql, tuple(vals))
    return True


# =========================================================================
# Workspace Branding
# =========================================================================

def get_branding(workspace_id: str) -> Optional[WorkspaceBranding]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM workspace_branding WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
    return row_to_model(row, WorkspaceBranding)


def upsert_branding(workspace_id: str, **kwargs) -> str:
    existing = get_branding(workspace_id)
    if existing:
        if not kwargs:
            return existing.id
        kwargs["updated_at"] = "datetime('now')"
        sets = []
        vals = []
        for k, v in kwargs.items():
            if v == "datetime('now')":
                sets.append(f"{k} = datetime('now')")
            else:
                sets.append(f"{k} = ?")
                vals.append(v if not isinstance(v, (dict, list)) else json.dumps(v))
        vals.append(workspace_id)
        sql = f"UPDATE workspace_branding SET {', '.join(sets)} WHERE workspace_id = ?"
        with get_db() as conn:
            conn.execute(sql, tuple(vals))
        return existing.id
    else:
        bid = _new_id()
        with get_db() as conn:
            conn.execute(
                "INSERT INTO workspace_branding (id, workspace_id) VALUES (?, ?)",
                (bid, workspace_id),
            )
        if kwargs:
            return upsert_branding(workspace_id, **kwargs)
        return bid


# =========================================================================
# API Keys
# =========================================================================

def create_api_key(workspace_id: str, created_by: str, key_hash: str,
                   key_prefix: str, name: str, permissions: dict) -> str:
    kid = _new_id()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO api_keys (id, workspace_id, created_by, key_hash, key_prefix, name, permissions)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (kid, workspace_id, created_by, key_hash, key_prefix, name, json.dumps(permissions)),
        )
    return kid


def get_api_keys_for_workspace(workspace_id: str) -> list[ApiKey]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM api_keys WHERE workspace_id = ? AND revoked_at IS NULL ORDER BY created_at DESC",
            (workspace_id,),
        ).fetchall()
    return rows_to_models(rows, ApiKey)


def get_api_key_by_prefix(key_prefix: str) -> Optional[ApiKey]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key_prefix = ? AND revoked_at IS NULL",
            (key_prefix,),
        ).fetchone()
    return row_to_model(row, ApiKey)


def revoke_api_key(key_id: str) -> bool:
    with get_db() as conn:
        conn.execute(
            "UPDATE api_keys SET revoked_at = datetime('now') WHERE id = ?",
            (key_id,),
        )
    return True


def update_api_key_last_used(key_id: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE api_keys SET last_used_at = datetime('now') WHERE id = ?",
            (key_id,),
        )


# =========================================================================
# Prompt History
# =========================================================================

def save_prompt_history(user_id: str, workspace_id: str, project_id: str,
                         prompt_text: str, file_id: str = None,
                         response_code: str = None, response_error: str = None,
                         tokens_used: int = 0, model_used: str = "") -> str:
    pid = _new_id()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO prompt_history
               (id, user_id, workspace_id, project_id, file_id, prompt_text, response_code, response_error, tokens_used, model_used)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (pid, user_id, workspace_id, project_id, file_id, prompt_text, response_code, response_error, tokens_used, model_used),
        )
    return pid


def get_prompt_history(workspace_id: str, project_id: str, limit: int = 50) -> list[PromptHistoryEntry]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM prompt_history
               WHERE workspace_id = ? AND project_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (workspace_id, project_id, limit),
        ).fetchall()
    return rows_to_models(rows, PromptHistoryEntry)
