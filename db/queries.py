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
    PromptHistoryEntry, PromptTemplate, AuditLogEntry, SystemSetting,
    UserPreferences,
    row_to_model, rows_to_models,
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

def create_project(workspace_id: str, created_by: str, name: str,
                   description: str = "", instructions: str = "") -> str:
    pid = _new_id()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO projects (id, workspace_id, created_by, name, description, instructions) VALUES (?, ?, ?, ?, ?, ?)",
            (pid, workspace_id, created_by, name, description, instructions),
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
            "SELECT balance_after FROM credit_ledger WHERE workspace_id = ? ORDER BY rowid DESC LIMIT 1",
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


# =========================================================================
# Prompt Templates
# =========================================================================

def create_prompt_template(project_id: str, created_by: str, name: str,
                           prompt_text: str, category: str = "") -> str:
    tid = _new_id()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO prompt_templates (id, project_id, created_by, name, prompt_text, category)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (tid, project_id, created_by, name, prompt_text, category),
        )
    return tid


def get_prompt_templates_for_project(project_id: str) -> list[PromptTemplate]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM prompt_templates WHERE project_id = ? ORDER BY usage_count DESC, name",
            (project_id,),
        ).fetchall()
    return rows_to_models(rows, PromptTemplate)


def get_prompt_template_by_id(template_id: str) -> Optional[PromptTemplate]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM prompt_templates WHERE id = ?", (template_id,)).fetchone()
    return row_to_model(row, PromptTemplate)


def update_prompt_template(template_id: str, **kwargs) -> bool:
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
    vals.append(template_id)
    sql = f"UPDATE prompt_templates SET {', '.join(sets)} WHERE id = ?"
    with get_db() as conn:
        conn.execute(sql, tuple(vals))
    return True


def delete_prompt_template(template_id: str) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM prompt_templates WHERE id = ?", (template_id,))
    return True


def increment_template_usage(template_id: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE prompt_templates SET usage_count = usage_count + 1 WHERE id = ?",
            (template_id,),
        )


# =========================================================================
# Usage Analytics (workspace-scoped, date-filtered)
# =========================================================================

def get_credits_used_in_range(workspace_id: str, start_date: str, end_date: str,
                              user_id: str = None) -> int:
    """Total credits consumed (deductions) within a date range."""
    params: list = [workspace_id, start_date, end_date]
    user_filter = ""
    if user_id:
        user_filter = "AND user_id = ?"
        params.append(user_id)
    with get_db() as conn:
        row = conn.execute(
            f"""SELECT COALESCE(SUM(ABS(change_amount)), 0) as total
                FROM credit_ledger
                WHERE workspace_id = ? AND change_amount < 0
                  AND date(created_at) >= ? AND date(created_at) <= ?
                  {user_filter}""",
            tuple(params),
        ).fetchone()
    return row["total"]


def get_analyses_count_in_range(workspace_id: str, start_date: str, end_date: str,
                                project_id: str = None, user_id: str = None) -> int:
    """Total number of AI analyses within a date range."""
    params: list = [workspace_id, start_date, end_date]
    filters = ""
    if project_id:
        filters += " AND project_id = ?"
        params.append(project_id)
    if user_id:
        filters += " AND user_id = ?"
        params.append(user_id)
    with get_db() as conn:
        row = conn.execute(
            f"""SELECT COUNT(*) as cnt FROM prompt_history
                WHERE workspace_id = ?
                  AND date(created_at) >= ? AND date(created_at) <= ?
                  {filters}""",
            tuple(params),
        ).fetchone()
    return row["cnt"]


def get_dashboards_created_in_range(workspace_id: str, start_date: str, end_date: str,
                                    project_id: str = None, user_id: str = None) -> int:
    """Count dashboards created within a date range."""
    params: list = [workspace_id, start_date, end_date]
    filters = ""
    if project_id:
        filters += " AND d.project_id = ?"
        params.append(project_id)
    if user_id:
        filters += " AND d.created_by = ?"
        params.append(user_id)
    with get_db() as conn:
        row = conn.execute(
            f"""SELECT COUNT(*) as cnt FROM dashboards d
                JOIN projects p ON d.project_id = p.id
                WHERE p.workspace_id = ?
                  AND date(d.created_at) >= ? AND date(d.created_at) <= ?
                  {filters}""",
            tuple(params),
        ).fetchone()
    return row["cnt"]


def get_credit_usage_by_day(workspace_id: str, start_date: str, end_date: str,
                            user_id: str = None) -> list[dict]:
    """Daily credit consumption (deductions only) within a date range."""
    params: list = [workspace_id, start_date, end_date]
    user_filter = ""
    if user_id:
        user_filter = "AND user_id = ?"
        params.append(user_id)
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT date(created_at) as date,
                       SUM(ABS(change_amount)) as credits_used
                FROM credit_ledger
                WHERE workspace_id = ? AND change_amount < 0
                  AND date(created_at) >= ? AND date(created_at) <= ?
                  {user_filter}
                GROUP BY date(created_at)
                ORDER BY date(created_at)""",
            tuple(params),
        ).fetchall()
    return [dict(r) for r in rows]


def get_analyses_by_day(workspace_id: str, start_date: str, end_date: str,
                        project_id: str = None, user_id: str = None) -> list[dict]:
    """Daily AI analysis count within a date range."""
    params: list = [workspace_id, start_date, end_date]
    filters = ""
    if project_id:
        filters += " AND project_id = ?"
        params.append(project_id)
    if user_id:
        filters += " AND user_id = ?"
        params.append(user_id)
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT date(created_at) as date,
                       COUNT(*) as analysis_count
                FROM prompt_history
                WHERE workspace_id = ?
                  AND date(created_at) >= ? AND date(created_at) <= ?
                  {filters}
                GROUP BY date(created_at)
                ORDER BY date(created_at)""",
            tuple(params),
        ).fetchall()
    return [dict(r) for r in rows]


def get_token_usage_by_project(workspace_id: str, start_date: str, end_date: str,
                               user_id: str = None) -> list[dict]:
    """Token usage grouped by project within a date range."""
    params: list = [workspace_id, start_date, end_date]
    user_filter = ""
    if user_id:
        user_filter = "AND ph.user_id = ?"
        params.append(user_id)
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT p.name as project_name, p.id as project_id,
                       SUM(ph.tokens_used) as total_tokens,
                       COUNT(*) as analysis_count
                FROM prompt_history ph
                JOIN projects p ON ph.project_id = p.id
                WHERE ph.workspace_id = ?
                  AND date(ph.created_at) >= ? AND date(ph.created_at) <= ?
                  {user_filter}
                GROUP BY ph.project_id
                ORDER BY total_tokens DESC""",
            tuple(params),
        ).fetchall()
    return [dict(r) for r in rows]


def get_uploads_in_range(workspace_id: str, start_date: str, end_date: str,
                         project_id: str = None, user_id: str = None) -> list[dict]:
    """File uploads within a date range, with format and project info."""
    params: list = [workspace_id, start_date, end_date]
    filters = ""
    if project_id:
        filters += " AND f.project_id = ?"
        params.append(project_id)
    if user_id:
        filters += " AND f.uploaded_by = ?"
        params.append(user_id)
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT f.id, f.original_filename, f.file_format, f.file_size_bytes,
                       f.row_count, f.uploaded_at, p.name as project_name
                FROM uploaded_files f
                JOIN projects p ON f.project_id = p.id
                WHERE p.workspace_id = ?
                  AND date(f.uploaded_at) >= ? AND date(f.uploaded_at) <= ?
                  {filters}
                ORDER BY f.uploaded_at DESC""",
            tuple(params),
        ).fetchall()
    return [dict(r) for r in rows]


def get_file_format_distribution(workspace_id: str, start_date: str, end_date: str,
                                 project_id: str = None) -> list[dict]:
    """File format distribution within a date range."""
    params: list = [workspace_id, start_date, end_date]
    filters = ""
    if project_id:
        filters += " AND f.project_id = ?"
        params.append(project_id)
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT f.file_format, COUNT(*) as count
                FROM uploaded_files f
                JOIN projects p ON f.project_id = p.id
                WHERE p.workspace_id = ?
                  AND date(f.uploaded_at) >= ? AND date(f.uploaded_at) <= ?
                  {filters}
                GROUP BY f.file_format
                ORDER BY count DESC""",
            tuple(params),
        ).fetchall()
    return [dict(r) for r in rows]


def get_recent_activity(workspace_id: str, start_date: str, end_date: str,
                        project_id: str = None, user_id: str = None,
                        limit: int = 50) -> list[dict]:
    """Unified activity feed: credit events + analyses, sorted by time."""
    credit_params: list = [workspace_id, start_date, end_date]
    prompt_params: list = [workspace_id, start_date, end_date]
    credit_filter = ""
    prompt_filter = ""
    if user_id:
        credit_filter += " AND user_id = ?"
        credit_params.append(user_id)
        prompt_filter += " AND user_id = ?"
        prompt_params.append(user_id)
    if project_id:
        prompt_filter += " AND project_id = ?"
        prompt_params.append(project_id)

    combined_params = credit_params + prompt_params + [limit]
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT 'credit' as activity_type, reason as description,
                       change_amount as detail_value, user_id, created_at
                FROM credit_ledger
                WHERE workspace_id = ?
                  AND date(created_at) >= ? AND date(created_at) <= ?
                  {credit_filter}
                UNION ALL
                SELECT 'analysis' as activity_type,
                       SUBSTR(prompt_text, 1, 80) as description,
                       tokens_used as detail_value, user_id, created_at
                FROM prompt_history
                WHERE workspace_id = ?
                  AND date(created_at) >= ? AND date(created_at) <= ?
                  {prompt_filter}
                ORDER BY created_at DESC
                LIMIT ?""",
            tuple(combined_params),
        ).fetchall()
    return [dict(r) for r in rows]


# =========================================================================
# Admin Queries (global — no workspace scoping)
# =========================================================================

def get_all_users(limit: int = 100, offset: int = 0) -> list[User]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return rows_to_models(rows, User)


def count_all_users() -> int:
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    return row["cnt"]


def get_all_workspaces(limit: int = 100, offset: int = 0) -> list[Workspace]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM workspaces ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return rows_to_models(rows, Workspace)


def count_all_workspaces() -> int:
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM workspaces").fetchone()
    return row["cnt"]


def get_all_subscriptions(status: str = None) -> list[Subscription]:
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM subscriptions WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM subscriptions ORDER BY created_at DESC"
            ).fetchall()
    return rows_to_models(rows, Subscription)


def count_subscriptions_by_tier() -> dict:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT tier, COUNT(*) as cnt FROM subscriptions WHERE status = 'active' GROUP BY tier"
        ).fetchall()
    return {row["tier"]: row["cnt"] for row in rows}


def get_total_credits_consumed() -> int:
    with get_db() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(ABS(change_amount)), 0) as total FROM credit_ledger WHERE change_amount < 0"
        ).fetchone()
    return row["total"]


def get_total_api_calls() -> int:
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM prompt_history").fetchone()
    return row["cnt"]


def get_total_revenue_cents() -> int:
    with get_db() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount_paid_cents), 0) as total FROM credit_purchases"
        ).fetchone()
    return row["total"]


def get_all_credit_purchases(limit: int = 100) -> list[CreditPurchase]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM credit_purchases ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return rows_to_models(rows, CreditPurchase)


def get_all_prompt_history(limit: int = 100, offset: int = 0) -> list[PromptHistoryEntry]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM prompt_history ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return rows_to_models(rows, PromptHistoryEntry)


def get_all_credit_ledger(limit: int = 100, offset: int = 0) -> list[CreditLedgerEntry]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM credit_ledger ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return rows_to_models(rows, CreditLedgerEntry)


# =========================================================================
# Audit Log
# =========================================================================

def create_audit_log(user_id: str, action: str, entity_type: str,
                     entity_id: str = None, details: str = None,
                     ip_address: str = None) -> str:
    aid = _new_id()
    detail_str = json.dumps(details) if isinstance(details, dict) else details
    with get_db() as conn:
        conn.execute(
            """INSERT INTO audit_log (id, user_id, action, entity_type, entity_id, details, ip_address)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (aid, user_id, action, entity_type, entity_id, detail_str, ip_address),
        )
    return aid


def get_audit_log(limit: int = 100, offset: int = 0,
                  entity_type: str = None, user_id: str = None) -> list[AuditLogEntry]:
    conditions = []
    params: list = []
    if entity_type:
        conditions.append("entity_type = ?")
        params.append(entity_type)
    if user_id:
        conditions.append("user_id = ?")
        params.append(user_id)
    where = " AND ".join(conditions) if conditions else "1=1"
    params.extend([limit, offset])
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM audit_log WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            tuple(params),
        ).fetchall()
    return rows_to_models(rows, AuditLogEntry)


# =========================================================================
# System Settings
# =========================================================================

def get_system_setting(key: str) -> Optional[str]:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM system_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_system_setting(key: str, value: str, updated_by: str) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO system_settings (key, value, updated_by, updated_at)
               VALUES (?, ?, ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET value = ?, updated_by = ?, updated_at = datetime('now')""",
            (key, value, updated_by, value, updated_by),
        )


def get_all_system_settings() -> dict:
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM system_settings ORDER BY key").fetchall()
    return {row["key"]: row["value"] for row in rows}


# =========================================================================
# Admin User Management
# =========================================================================

def set_user_superadmin(user_id: str, is_superadmin: bool) -> bool:
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET is_superadmin = ?, updated_at = datetime('now') WHERE id = ?",
            (1 if is_superadmin else 0, user_id),
        )
    return True


def set_superadmin_by_email(email: str) -> bool:
    """Set superadmin flag for user by email. Called during init."""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET is_superadmin = 1, updated_at = datetime('now') WHERE email = ?",
            (email.strip().lower(),),
        )
    return True


# =========================================================================
# File Upload Status
# =========================================================================

def update_file_status(file_id: str, status: str, error_message: str = None) -> bool:
    """Update the processing status of an uploaded file."""
    with get_db() as conn:
        conn.execute(
            "UPDATE uploaded_files SET status = ?, error_message = ? WHERE id = ?",
            (status, error_message, file_id),
        )
    return True


# =========================================================================
# Project Activity Summary
# =========================================================================

def get_project_activity_summary(project_id: str) -> dict:
    """Aggregate activity stats for a project."""
    with get_db() as conn:
        files_row = conn.execute(
            """SELECT COUNT(*) as total,
                      SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success,
                      SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors,
                      SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending
               FROM uploaded_files WHERE project_id = ?""",
            (project_id,),
        ).fetchone()
        dash_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM dashboards WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        analysis_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM prompt_history WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        last_row = conn.execute(
            """SELECT MAX(ts) as last_at FROM (
                SELECT uploaded_at as ts FROM uploaded_files WHERE project_id = ?
                UNION ALL
                SELECT created_at as ts FROM prompt_history WHERE project_id = ?
                UNION ALL
                SELECT created_at as ts FROM dashboards WHERE project_id = ?
            )""",
            (project_id, project_id, project_id),
        ).fetchone()
    return {
        "files_total": files_row["total"] or 0,
        "files_success": files_row["success"] or 0,
        "files_error": files_row["errors"] or 0,
        "files_pending": files_row["pending"] or 0,
        "dashboards_count": dash_row["cnt"] or 0,
        "analyses_count": analysis_row["cnt"] or 0,
        "last_activity": last_row["last_at"],
    }


# =========================================================================
# User Preferences
# =========================================================================

def get_user_preferences(user_id: str) -> Optional[UserPreferences]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return row_to_model(row, UserPreferences)


def upsert_user_preferences(user_id: str, **kwargs) -> str:
    existing = get_user_preferences(user_id)
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
                vals.append(v)
        vals.append(user_id)
        sql = f"UPDATE user_preferences SET {', '.join(sets)} WHERE user_id = ?"
        with get_db() as conn:
            conn.execute(sql, tuple(vals))
        return existing.id
    else:
        pid = _new_id()
        cols = ["id", "user_id"]
        placeholders = ["?", "?"]
        vals = [pid, user_id]
        for k, v in kwargs.items():
            if k == "updated_at":
                continue
            cols.append(k)
            placeholders.append("?")
            vals.append(v)
        sql = f"INSERT INTO user_preferences ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
        with get_db() as conn:
            conn.execute(sql, tuple(vals))
        return pid


# =========================================================================
# Trial Status
# =========================================================================

def is_workspace_in_trial(workspace_id: str) -> bool:
    """Check if workspace is in an active trial period."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT trial_ends_at FROM workspaces WHERE id = ? AND trial_ends_at > datetime('now')",
            (workspace_id,),
        ).fetchone()
    return row is not None
