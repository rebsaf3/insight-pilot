"""SQLite database connection manager and schema initialization."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config.settings import DB_PATH

# ---------------------------------------------------------------------------
# Schema DDL — executed once on first run via init_db()
# ---------------------------------------------------------------------------

_SCHEMA = """
-- =========================================================================
-- Core User & Auth
-- =========================================================================

CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL DEFAULT '',
    display_name    TEXT NOT NULL DEFAULT '',
    avatar_url      TEXT DEFAULT NULL,
    totp_secret     TEXT DEFAULT NULL,
    totp_enabled    INTEGER NOT NULL DEFAULT 0,
    email_2fa_enabled INTEGER NOT NULL DEFAULT 0,
    sso_provider    TEXT DEFAULT NULL,
    sso_provider_id TEXT DEFAULT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS email_verification_codes (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code            TEXT NOT NULL,
    purpose         TEXT NOT NULL,
    expires_at      TEXT NOT NULL,
    used_at         TEXT DEFAULT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_evc_user_id ON email_verification_codes(user_id);

CREATE TABLE IF NOT EXISTS user_sessions (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token   TEXT UNIQUE NOT NULL,
    ip_address      TEXT DEFAULT NULL,
    user_agent      TEXT DEFAULT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);

CREATE TABLE IF NOT EXISTS backup_codes (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash       TEXT NOT NULL,
    used_at         TEXT DEFAULT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_backup_user_id ON backup_codes(user_id);

-- =========================================================================
-- Workspaces & Access Control
-- =========================================================================

CREATE TABLE IF NOT EXISTS workspaces (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    owner_id        TEXT NOT NULL REFERENCES users(id),
    tier            TEXT NOT NULL DEFAULT 'free',
    stripe_customer_id TEXT DEFAULT NULL,
    sso_enabled     INTEGER NOT NULL DEFAULT 0,
    sso_config      TEXT DEFAULT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_workspaces_owner ON workspaces(owner_id);

CREATE TABLE IF NOT EXISTS workspace_members (
    id              TEXT PRIMARY KEY,
    workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            TEXT NOT NULL DEFAULT 'member',
    invited_by      TEXT DEFAULT NULL REFERENCES users(id),
    joined_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(workspace_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_wm_workspace ON workspace_members(workspace_id);
CREATE INDEX IF NOT EXISTS idx_wm_user ON workspace_members(user_id);

CREATE TABLE IF NOT EXISTS workspace_invitations (
    id              TEXT PRIMARY KEY,
    workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    email           TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'member',
    invited_by      TEXT NOT NULL REFERENCES users(id),
    token           TEXT UNIQUE NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_wi_workspace ON workspace_invitations(workspace_id);
CREATE INDEX IF NOT EXISTS idx_wi_token ON workspace_invitations(token);
CREATE INDEX IF NOT EXISTS idx_wi_email ON workspace_invitations(email);

-- =========================================================================
-- Data & Projects
-- =========================================================================

CREATE TABLE IF NOT EXISTS projects (
    id              TEXT PRIMARY KEY,
    workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    created_by      TEXT NOT NULL REFERENCES users(id),
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_projects_workspace ON projects(workspace_id);

CREATE TABLE IF NOT EXISTS uploaded_files (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    uploaded_by     TEXT NOT NULL REFERENCES users(id),
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    file_format     TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    row_count       INTEGER DEFAULT NULL,
    column_count    INTEGER DEFAULT NULL,
    column_names    TEXT DEFAULT NULL,
    data_profile    TEXT DEFAULT NULL,
    uploaded_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_files_project ON uploaded_files(project_id);

CREATE TABLE IF NOT EXISTS dashboards (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_by      TEXT NOT NULL REFERENCES users(id),
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    layout          TEXT NOT NULL DEFAULT '[]',
    style_config    TEXT DEFAULT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_dashboards_project ON dashboards(project_id);

CREATE TABLE IF NOT EXISTS charts (
    id              TEXT PRIMARY KEY,
    dashboard_id    TEXT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
    file_id         TEXT NOT NULL REFERENCES uploaded_files(id),
    title           TEXT NOT NULL DEFAULT 'Untitled Chart',
    chart_type      TEXT DEFAULT NULL,
    user_prompt     TEXT NOT NULL,
    generated_code  TEXT NOT NULL,
    plotly_json     TEXT DEFAULT NULL,
    style_overrides TEXT DEFAULT NULL,
    position_index  INTEGER NOT NULL DEFAULT 0,
    created_by      TEXT NOT NULL REFERENCES users(id),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_charts_dashboard ON charts(dashboard_id);

-- =========================================================================
-- Billing & Credits
-- =========================================================================

CREATE TABLE IF NOT EXISTS credit_ledger (
    id              TEXT PRIMARY KEY,
    workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id         TEXT NOT NULL REFERENCES users(id),
    change_amount   INTEGER NOT NULL,
    balance_after   INTEGER NOT NULL,
    reason          TEXT NOT NULL,
    reference_id    TEXT DEFAULT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cl_workspace ON credit_ledger(workspace_id);
CREATE INDEX IF NOT EXISTS idx_cl_user ON credit_ledger(user_id);

CREATE TABLE IF NOT EXISTS subscriptions (
    id              TEXT PRIMARY KEY,
    workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    tier            TEXT NOT NULL DEFAULT 'free',
    stripe_subscription_id TEXT DEFAULT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    current_period_start TEXT DEFAULT NULL,
    current_period_end   TEXT DEFAULT NULL,
    monthly_credit_allowance INTEGER NOT NULL DEFAULT 50,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_subs_workspace ON subscriptions(workspace_id);

CREATE TABLE IF NOT EXISTS credit_purchases (
    id              TEXT PRIMARY KEY,
    workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    purchased_by    TEXT NOT NULL REFERENCES users(id),
    stripe_payment_id TEXT DEFAULT NULL,
    credits_purchased INTEGER NOT NULL,
    amount_paid_cents INTEGER NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cp_workspace ON credit_purchases(workspace_id);

CREATE TABLE IF NOT EXISTS add_ons (
    id              TEXT PRIMARY KEY,
    workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    add_on_type     TEXT NOT NULL,
    stripe_subscription_id TEXT DEFAULT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_addons_workspace ON add_ons(workspace_id);

-- =========================================================================
-- Branding
-- =========================================================================

CREATE TABLE IF NOT EXISTS workspace_branding (
    id              TEXT PRIMARY KEY,
    workspace_id    TEXT UNIQUE NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    logo_path       TEXT DEFAULT NULL,
    primary_color   TEXT NOT NULL DEFAULT '#1E88E5',
    secondary_color TEXT NOT NULL DEFAULT '#F5F5F5',
    accent_color    TEXT NOT NULL DEFAULT '#FF6F00',
    font_family     TEXT NOT NULL DEFAULT 'Inter',
    font_size_base  INTEGER NOT NULL DEFAULT 14,
    chart_color_palette TEXT NOT NULL DEFAULT '["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b"]',
    header_text     TEXT NOT NULL DEFAULT '',
    footer_text     TEXT NOT NULL DEFAULT '',
    hide_insightpilot_branding INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- =========================================================================
-- API
-- =========================================================================

CREATE TABLE IF NOT EXISTS api_keys (
    id              TEXT PRIMARY KEY,
    workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    created_by      TEXT NOT NULL REFERENCES users(id),
    key_hash        TEXT NOT NULL,
    key_prefix      TEXT NOT NULL,
    name            TEXT NOT NULL DEFAULT '',
    permissions     TEXT NOT NULL DEFAULT '{"read":true,"write":true,"analyze":true}',
    last_used_at    TEXT DEFAULT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    revoked_at      TEXT DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_ak_workspace ON api_keys(workspace_id);
CREATE INDEX IF NOT EXISTS idx_ak_prefix ON api_keys(key_prefix);

-- =========================================================================
-- Prompt Tracking
-- =========================================================================

CREATE TABLE IF NOT EXISTS prompt_history (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id),
    workspace_id    TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    project_id      TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    file_id         TEXT DEFAULT NULL REFERENCES uploaded_files(id),
    prompt_text     TEXT NOT NULL,
    response_code   TEXT DEFAULT NULL,
    response_error  TEXT DEFAULT NULL,
    tokens_used     INTEGER NOT NULL DEFAULT 0,
    model_used      TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ph_user ON prompt_history(user_id);
CREATE INDEX IF NOT EXISTS idx_ph_workspace ON prompt_history(workspace_id);
"""


def _ensure_db_dir() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with WAL mode and foreign keys enabled."""
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """Context manager that yields a connection and commits on success."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create all tables if they do not exist. Safe to call multiple times."""
    with get_db() as conn:
        conn.executescript(_SCHEMA)


def execute_query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Run a SELECT and return all rows."""
    with get_db() as conn:
        return conn.execute(sql, params).fetchall()


def execute_write(sql: str, params: tuple = ()) -> int:
    """Run an INSERT / UPDATE / DELETE. Returns lastrowid for inserts."""
    with get_db() as conn:
        cursor = conn.execute(sql, params)
        return cursor.lastrowid
