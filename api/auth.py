"""API key authentication middleware."""

import hashlib
from typing import Optional

from fastapi import Header, HTTPException, Depends

from db import queries
from db.models import ApiKey, Workspace


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def get_api_key(authorization: str = Header(None)) -> ApiKey:
    """Validate API key from Authorization header.
    Expected format: Bearer ip_xxxxxxxx..."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization format. Use: Bearer <api_key>")

    raw_key = parts[1]
    if not raw_key.startswith("ip_"):
        raise HTTPException(status_code=401, detail="Invalid API key format")

    prefix = raw_key[:11]  # "ip_" + first 8 chars
    api_key = queries.get_api_key_by_prefix(prefix)

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if api_key.revoked_at:
        raise HTTPException(status_code=401, detail="API key has been revoked")

    # Verify full key hash
    key_hash = _hash_key(raw_key)
    if key_hash != api_key.key_hash:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Update last used
    queries.update_api_key_last_used(api_key.id)

    return api_key


async def get_workspace_from_key(api_key: ApiKey = Depends(get_api_key)) -> Workspace:
    """Get the workspace associated with the API key."""
    ws = queries.get_workspace_by_id(api_key.workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Check that API add-on is active
    addon = queries.get_add_on(ws.id, "api_access")
    if not addon:
        raise HTTPException(status_code=403, detail="API access add-on is not active for this workspace")

    return ws


def require_permission(permission: str):
    """Dependency that checks API key has a specific permission."""
    async def _check(api_key: ApiKey = Depends(get_api_key)):
        perms = api_key.permissions or {}
        if not perms.get(permission, False):
            raise HTTPException(status_code=403, detail=f"API key lacks '{permission}' permission")
        return api_key
    return _check
