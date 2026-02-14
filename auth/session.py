"""Session management — tracks current user and workspace in Streamlit session state."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import streamlit as st

from config.settings import SESSION_EXPIRY_DAYS, ROLE_PERMISSIONS
from db import queries
from db.models import User, Workspace


def _generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def create_user_session(user: User) -> str:
    """Create a new session for the authenticated user. Returns the session token."""
    token = _generate_session_token()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat()
    queries.create_session(
        user_id=user.id,
        session_token=token,
        expires_at=expires_at,
    )
    # Store in Streamlit session state
    st.session_state["session_token"] = token
    st.session_state["user_id"] = user.id
    return token


def create_user_session_headless(user: User) -> str:
    """Create a session without Streamlit (for SSO callbacks in FastAPI)."""
    token = _generate_session_token()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat()
    queries.create_session(
        user_id=user.id,
        session_token=token,
        expires_at=expires_at,
    )
    return token


def get_current_user() -> Optional[User]:
    """Return the current authenticated User, or None."""
    user_id = st.session_state.get("user_id")
    if not user_id:
        token = st.session_state.get("session_token")
        if not token:
            return None
        session = queries.get_session_by_token(token)
        if not session:
            return None
        st.session_state["user_id"] = session.user_id
        user_id = session.user_id
    return queries.get_user_by_id(user_id)


def require_auth() -> User:
    """Require authentication. Stops the page if not logged in."""
    user = get_current_user()
    if not user:
        st.warning("Please log in to continue.")
        st.stop()
    return user


def logout() -> None:
    """Log out the current user — delete session and clear state."""
    token = st.session_state.get("session_token")
    if token:
        queries.delete_session_by_token(token)
    for key in ["session_token", "user_id", "current_workspace_id", "current_project_id"]:
        st.session_state.pop(key, None)


# ---------------------------------------------------------------------------
# Workspace context
# ---------------------------------------------------------------------------

def get_current_workspace() -> Optional[Workspace]:
    """Return the currently selected workspace."""
    ws_id = st.session_state.get("current_workspace_id")
    if not ws_id:
        return None
    return queries.get_workspace_by_id(ws_id)


def set_current_workspace(workspace_id: str) -> None:
    """Set the active workspace. Clears project selection."""
    st.session_state["current_workspace_id"] = workspace_id
    st.session_state.pop("current_project_id", None)


def get_current_project_id() -> Optional[str]:
    return st.session_state.get("current_project_id")


def set_current_project(project_id: str) -> None:
    st.session_state["current_project_id"] = project_id


# ---------------------------------------------------------------------------
# Permission checks
# ---------------------------------------------------------------------------

def get_user_role_in_workspace(user_id: str, workspace_id: str) -> Optional[str]:
    """Return the user's role in the workspace, or None if not a member."""
    return queries.get_member_role(workspace_id, user_id)


def user_has_permission(user_id: str, workspace_id: str, permission: str) -> bool:
    """Check if a user has a specific permission in a workspace."""
    role = get_user_role_in_workspace(user_id, workspace_id)
    if not role:
        return False
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(permission: str) -> tuple[User, Workspace]:
    """Require both auth and a specific permission. Stops the page if not authorized."""
    user = require_auth()
    ws = get_current_workspace()
    if not ws:
        st.warning("Please select a workspace.")
        st.stop()
    if not user_has_permission(user.id, ws.id, permission):
        st.error("You don't have permission to access this feature.")
        st.stop()
    return user, ws


def require_superadmin() -> User:
    """Require superadmin access. Stops the page if not a superadmin."""
    user = require_auth()
    if not getattr(user, "is_superadmin", False):
        st.error("Access denied. This section is restricted to system administrators.")
        st.stop()
    return user
