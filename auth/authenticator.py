"""Authentication module — handles registration, login, password hashing."""

import bcrypt

from db import queries
from db.models import User
from typing import Optional


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def register_user(email: str, password: str, display_name: str) -> tuple[bool, str]:
    """Register a new user. Returns (success, user_id_or_error_message)."""
    email = email.strip().lower()
    if not email or not password:
        return False, "Email and password are required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."

    existing = queries.get_user_by_email(email)
    if existing:
        return False, "An account with this email already exists."

    pw_hash = hash_password(password)
    user_id = queries.create_user(email=email, password_hash=pw_hash, display_name=display_name)
    return True, user_id


def authenticate(email: str, password: str) -> tuple[bool, Optional[User], str]:
    """Authenticate with email + password.
    Returns (success, user_or_none, error_message).
    On success, caller must still check user.has_2fa to decide if 2FA is needed."""
    email = email.strip().lower()
    user = queries.get_user_by_email(email)
    if not user:
        return False, None, "Invalid email or password."
    if not user.password_hash:
        return False, None, "This account uses SSO. Please sign in with your identity provider."
    if not verify_password(password, user.password_hash):
        return False, None, "Invalid email or password."
    return True, user, ""
