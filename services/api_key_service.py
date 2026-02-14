"""API key service — create, verify, and manage API keys."""

import hashlib
import secrets
from typing import Optional

from db import queries
from db.models import ApiKey


API_KEY_PREFIX = "ip_"


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.
    Returns (full_key, key_hash, key_prefix).
    The full key is shown once to the user, then only the prefix is stored.
    """
    raw = secrets.token_urlsafe(32)
    full_key = f"{API_KEY_PREFIX}{raw}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    key_prefix = full_key[:12]
    return full_key, key_hash, key_prefix


def create_api_key(workspace_id: str, created_by: str, name: str,
                   permissions: dict = None) -> tuple[str, str]:
    """Create a new API key. Returns (full_key, key_id).
    full_key is shown once — store it securely.
    """
    if permissions is None:
        permissions = {"read": True, "write": True, "analyze": True}

    full_key, key_hash, key_prefix = generate_api_key()
    key_id = queries.create_api_key(
        workspace_id=workspace_id,
        created_by=created_by,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
        permissions=permissions,
    )
    return full_key, key_id


def verify_api_key(api_key: str) -> Optional[ApiKey]:
    """Verify an API key and return the ApiKey record if valid."""
    if not api_key or not api_key.startswith(API_KEY_PREFIX):
        return None

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_prefix = api_key[:12]

    # Look up by prefix first for efficiency
    key_record = queries.get_api_key_by_prefix(key_prefix)
    if not key_record:
        return None

    # Verify full hash
    if key_record.key_hash != key_hash:
        return None

    # Update last used
    queries.update_api_key_last_used(key_record.id)
    return key_record


def revoke_api_key(key_id: str) -> bool:
    """Revoke an API key."""
    return queries.revoke_api_key(key_id)


def list_api_keys(workspace_id: str) -> list[ApiKey]:
    """List all active API keys for a workspace."""
    return queries.get_api_keys_for_workspace(workspace_id)


def has_api_access(workspace_id: str) -> bool:
    """Check if workspace has the API access add-on."""
    addon = queries.get_add_on(workspace_id, "api_access")
    return addon is not None and addon.status == "active"
