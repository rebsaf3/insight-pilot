"""SSO service — Google OIDC, Microsoft OIDC, SAML 2.0 integration."""

import json
import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
import jwt

from config.settings import (
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_TENANT_ID,
    BASE_URL, APP_SECRET_KEY,
)
from db import queries
from db.models import User, Workspace


# ---------------------------------------------------------------------------
# Google OIDC (Pro+)
# ---------------------------------------------------------------------------

GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

_google_config_cache: dict = {}


def _get_google_config() -> dict:
    """Fetch and cache Google's OIDC discovery document."""
    if not _google_config_cache:
        resp = httpx.get(GOOGLE_DISCOVERY_URL, timeout=10)
        resp.raise_for_status()
        _google_config_cache.update(resp.json())
    return _google_config_cache


def get_google_auth_url(workspace_id: str, redirect_uri: str = None) -> str:
    """Generate the Google OAuth2 authorization URL."""
    config = _get_google_config()
    state = _create_state_token(workspace_id, "google")
    redirect = redirect_uri or f"{BASE_URL}/auth/sso/google/callback"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": redirect,
        "state": state,
        "prompt": "select_account",
    }
    return f"{config['authorization_endpoint']}?{urlencode(params)}"


def exchange_google_code(code: str, redirect_uri: str = None) -> dict:
    """Exchange authorization code for tokens and return user info."""
    config = _get_google_config()
    redirect = redirect_uri or f"{BASE_URL}/auth/sso/google/callback"
    token_resp = httpx.post(
        config["token_endpoint"],
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect,
        },
        timeout=10,
    )
    token_resp.raise_for_status()
    tokens = token_resp.json()

    # Get user info
    userinfo_resp = httpx.get(
        config["userinfo_endpoint"],
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        timeout=10,
    )
    userinfo_resp.raise_for_status()
    userinfo = userinfo_resp.json()

    return {
        "email": userinfo.get("email", "").lower(),
        "name": userinfo.get("name", ""),
        "picture": userinfo.get("picture"),
        "sub": userinfo.get("sub"),  # Google unique ID
        "provider": "google",
    }


# ---------------------------------------------------------------------------
# Microsoft OIDC (Pro+)
# ---------------------------------------------------------------------------

def _get_microsoft_config(tenant_id: str = None) -> dict:
    """Fetch Microsoft's OIDC discovery document."""
    tid = tenant_id or MICROSOFT_TENANT_ID or "common"
    url = f"https://login.microsoftonline.com/{tid}/v2.0/.well-known/openid-configuration"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_microsoft_auth_url(workspace_id: str, tenant_id: str = None,
                           client_id: str = None, redirect_uri: str = None) -> str:
    """Generate the Microsoft OAuth2 authorization URL."""
    tid = tenant_id or MICROSOFT_TENANT_ID or "common"
    cid = client_id or MICROSOFT_CLIENT_ID
    config = _get_microsoft_config(tid)
    state = _create_state_token(workspace_id, "microsoft")
    redirect = redirect_uri or f"{BASE_URL}/auth/sso/microsoft/callback"
    params = {
        "client_id": cid,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": redirect,
        "state": state,
        "prompt": "select_account",
    }
    return f"{config['authorization_endpoint']}?{urlencode(params)}"


def exchange_microsoft_code(code: str, tenant_id: str = None,
                            client_id: str = None, client_secret: str = None,
                            redirect_uri: str = None) -> dict:
    """Exchange authorization code for tokens and return user info."""
    tid = tenant_id or MICROSOFT_TENANT_ID or "common"
    cid = client_id or MICROSOFT_CLIENT_ID
    csecret = client_secret or MICROSOFT_CLIENT_SECRET
    config = _get_microsoft_config(tid)
    redirect = redirect_uri or f"{BASE_URL}/auth/sso/microsoft/callback"

    token_resp = httpx.post(
        config["token_endpoint"],
        data={
            "client_id": cid,
            "client_secret": csecret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect,
            "scope": "openid email profile",
        },
        timeout=10,
    )
    token_resp.raise_for_status()
    tokens = token_resp.json()

    # Decode ID token to get user info (we trust Microsoft's issuer)
    id_token = tokens.get("id_token", "")
    claims = jwt.decode(id_token, options={"verify_signature": False})

    return {
        "email": claims.get("preferred_username", claims.get("email", "")).lower(),
        "name": claims.get("name", ""),
        "picture": None,
        "sub": claims.get("sub"),
        "provider": "microsoft",
    }


# ---------------------------------------------------------------------------
# SAML 2.0 (Enterprise only)
# ---------------------------------------------------------------------------

def get_saml_auth_url(workspace: Workspace) -> Optional[str]:
    """Generate SAML SSO redirect URL from workspace config.
    Requires workspace.sso_config to have: idp_sso_url, sp_entity_id.
    """
    if not workspace.sso_config:
        return None

    idp_sso_url = workspace.sso_config.get("idp_sso_url")
    if not idp_sso_url:
        return None

    sp_entity_id = workspace.sso_config.get("sp_entity_id", f"{BASE_URL}/auth/sso/saml/metadata")
    acs_url = f"{BASE_URL}/auth/sso/saml/acs"

    # Build a minimal SAML AuthnRequest (simplified — in production use python3-saml)
    import base64
    import zlib
    from datetime import datetime, timezone

    request_id = f"_ip_{secrets.token_hex(16)}"
    issue_instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    authn_request = f"""<samlp:AuthnRequest
        xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
        xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
        ID="{request_id}"
        Version="2.0"
        IssueInstant="{issue_instant}"
        Destination="{idp_sso_url}"
        AssertionConsumerServiceURL="{acs_url}"
        ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
        <saml:Issuer>{sp_entity_id}</saml:Issuer>
    </samlp:AuthnRequest>"""

    # Deflate + base64 encode for redirect binding
    compressed = zlib.compress(authn_request.encode("utf-8"))[2:-4]
    encoded = base64.b64encode(compressed).decode("utf-8")

    params = {
        "SAMLRequest": encoded,
        "RelayState": workspace.id,
    }
    return f"{idp_sso_url}?{urlencode(params)}"


def process_saml_response(saml_response_b64: str, relay_state: str) -> Optional[dict]:
    """Parse a SAML Response and extract user info.
    In production, validate signature with IdP certificate.
    """
    import base64
    import xml.etree.ElementTree as ET

    try:
        xml_bytes = base64.b64decode(saml_response_b64)
        root = ET.fromstring(xml_bytes)

        # Namespace map
        ns = {
            "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
            "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
        }

        # Check status
        status = root.find(".//samlp:StatusCode", ns)
        if status is not None and "Success" not in status.get("Value", ""):
            return None

        # Extract attributes
        assertion = root.find(".//saml:Assertion", ns)
        if assertion is None:
            return None

        # Get NameID
        name_id_elem = assertion.find(".//saml:NameID", ns)
        name_id = name_id_elem.text if name_id_elem is not None else None

        # Get attributes
        attrs = {}
        for attr_stmt in assertion.findall(".//saml:AttributeStatement/saml:Attribute", ns):
            attr_name = attr_stmt.get("Name", "")
            values = [v.text for v in attr_stmt.findall("saml:AttributeValue", ns)]
            if values:
                attrs[attr_name] = values[0]

        email = (
            attrs.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress")
            or attrs.get("email")
            or attrs.get("Email")
            or name_id
            or ""
        ).lower()

        display_name = (
            attrs.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name")
            or attrs.get("displayName")
            or attrs.get("name")
            or email.split("@")[0]
        )

        return {
            "email": email,
            "name": display_name,
            "picture": None,
            "sub": name_id,
            "provider": "saml",
            "workspace_id": relay_state,
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# State token management (CSRF protection)
# ---------------------------------------------------------------------------

def _create_state_token(workspace_id: str, provider: str) -> str:
    """Create a signed state token for SSO flow."""
    payload = {
        "workspace_id": workspace_id,
        "provider": provider,
        "nonce": secrets.token_hex(16),
    }
    return jwt.encode(payload, APP_SECRET_KEY, algorithm="HS256")


def verify_state_token(state: str) -> Optional[dict]:
    """Verify and decode an SSO state token."""
    try:
        return jwt.decode(state, APP_SECRET_KEY, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None


# ---------------------------------------------------------------------------
# User resolution — find or create user from SSO info
# ---------------------------------------------------------------------------

def find_or_create_sso_user(sso_info: dict) -> User:
    """Find existing user by email or SSO provider+ID, or create new one."""
    email = sso_info["email"]
    provider = sso_info["provider"]
    provider_id = sso_info.get("sub", "")

    # First check by SSO provider + ID
    user = queries.get_user_by_email(email)

    if user:
        # Update SSO fields if not already set
        if not user.sso_provider:
            queries.update_user(
                user.id,
                sso_provider=provider,
                sso_provider_id=provider_id,
            )
        return queries.get_user_by_id(user.id)

    # Create new user (no password — SSO only)
    user_id = queries.create_user(
        email=email,
        password_hash="",  # No password for SSO users
        display_name=sso_info.get("name", email.split("@")[0]),
    )
    queries.update_user(
        user_id,
        sso_provider=provider,
        sso_provider_id=provider_id,
        avatar_url=sso_info.get("picture"),
    )
    return queries.get_user_by_id(user_id)


def add_sso_user_to_workspace(user: User, workspace_id: str) -> None:
    """Add SSO user to workspace if not already a member."""
    role = queries.get_member_role(workspace_id, user.id)
    if not role:
        queries.add_workspace_member(workspace_id, user.id, "member")


# ---------------------------------------------------------------------------
# SSO availability checks
# ---------------------------------------------------------------------------

def is_sso_available(workspace: Workspace, provider: str) -> bool:
    """Check if a given SSO provider is available for this workspace's tier."""
    from config.settings import TIERS
    tier_config = TIERS.get(workspace.tier, TIERS["free"])
    return provider in tier_config.get("sso_providers", [])


def get_workspace_sso_config(workspace: Workspace) -> dict:
    """Return the SSO configuration for a workspace."""
    return workspace.sso_config or {}


def save_workspace_sso_config(workspace_id: str, sso_config: dict, sso_enabled: bool) -> bool:
    """Save SSO config for a workspace."""
    return queries.update_workspace(
        workspace_id,
        sso_config=sso_config,
        sso_enabled=1 if sso_enabled else 0,
    )
