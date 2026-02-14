"""SSO callback handlers for FastAPI — Google OIDC, Microsoft OIDC, SAML."""

from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import RedirectResponse, HTMLResponse

from services.sso_service import (
    exchange_google_code, exchange_microsoft_code,
    process_saml_response, verify_state_token,
    find_or_create_sso_user, add_sso_user_to_workspace,
)
from services.workspace_service import create_personal_workspace
from auth.session import create_user_session_headless
from db import queries
from config.settings import BASE_URL

router = APIRouter()


def _build_streamlit_redirect(session_token: str, user_id: str) -> str:
    """Build a redirect URL back to the Streamlit app with session info.
    Uses a simple HTML page that sets localStorage and redirects."""
    return f"""
    <html>
    <head><title>Signing in...</title></head>
    <body>
    <script>
        // Store session info for Streamlit to pick up
        window.localStorage.setItem('ip_sso_session', JSON.stringify({{
            session_token: '{session_token}',
            user_id: '{user_id}'
        }}));
        window.location.href = '/';
    </script>
    <p>Signing you in... If not redirected, <a href="/">click here</a>.</p>
    </body>
    </html>
    """


@router.get("/auth/sso/google/callback")
async def google_callback(request: Request):
    """Handle Google OIDC callback."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        raise HTTPException(status_code=400, detail=f"Google SSO error: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")

    # Verify state token
    state_data = verify_state_token(state)
    if not state_data or state_data.get("provider") != "google":
        raise HTTPException(status_code=400, detail="Invalid state token")

    workspace_id = state_data.get("workspace_id")

    # Exchange code for user info
    try:
        sso_info = exchange_google_code(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to authenticate with Google: {e}")

    # Find or create user
    user = find_or_create_sso_user(sso_info)

    # Ensure personal workspace exists
    user_workspaces = queries.get_workspaces_for_user(user.id)
    if not user_workspaces:
        create_personal_workspace(user.id, user.display_name)

    # Add to workspace if specified
    if workspace_id:
        add_sso_user_to_workspace(user, workspace_id)

    # Create session
    session_token = create_user_session_headless(user)

    return HTMLResponse(_build_streamlit_redirect(session_token, user.id))


@router.get("/auth/sso/microsoft/callback")
async def microsoft_callback(request: Request):
    """Handle Microsoft OIDC callback."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")
    error_desc = request.query_params.get("error_description", "")

    if error:
        raise HTTPException(status_code=400, detail=f"Microsoft SSO error: {error} — {error_desc}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")

    state_data = verify_state_token(state)
    if not state_data or state_data.get("provider") != "microsoft":
        raise HTTPException(status_code=400, detail="Invalid state token")

    workspace_id = state_data.get("workspace_id")

    # Optionally use workspace-specific tenant config
    tenant_id = None
    client_id = None
    client_secret = None
    if workspace_id:
        ws = queries.get_workspace_by_id(workspace_id)
        if ws and ws.sso_config:
            tenant_id = ws.sso_config.get("microsoft_tenant_id")
            client_id = ws.sso_config.get("microsoft_client_id")
            client_secret = ws.sso_config.get("microsoft_client_secret")

    try:
        sso_info = exchange_microsoft_code(
            code,
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to authenticate with Microsoft: {e}")

    user = find_or_create_sso_user(sso_info)

    user_workspaces = queries.get_workspaces_for_user(user.id)
    if not user_workspaces:
        create_personal_workspace(user.id, user.display_name)

    if workspace_id:
        add_sso_user_to_workspace(user, workspace_id)

    session_token = create_user_session_headless(user)
    return HTMLResponse(_build_streamlit_redirect(session_token, user.id))


@router.post("/auth/sso/saml/acs")
async def saml_acs(SAMLResponse: str = Form(...), RelayState: str = Form("")):
    """Handle SAML Assertion Consumer Service (ACS) callback."""
    sso_info = process_saml_response(SAMLResponse, RelayState)
    if not sso_info:
        raise HTTPException(status_code=400, detail="Invalid SAML response")

    workspace_id = sso_info.get("workspace_id")

    # Verify workspace allows SAML
    if workspace_id:
        ws = queries.get_workspace_by_id(workspace_id)
        if not ws or not ws.sso_enabled:
            raise HTTPException(status_code=403, detail="SSO not enabled for this workspace")

    user = find_or_create_sso_user(sso_info)

    user_workspaces = queries.get_workspaces_for_user(user.id)
    if not user_workspaces:
        create_personal_workspace(user.id, user.display_name)

    if workspace_id:
        add_sso_user_to_workspace(user, workspace_id)

    session_token = create_user_session_headless(user)
    return HTMLResponse(_build_streamlit_redirect(session_token, user.id))


@router.get("/auth/sso/saml/metadata")
async def saml_metadata():
    """Return SP metadata for SAML configuration."""
    sp_entity_id = f"{BASE_URL}/auth/sso/saml/metadata"
    acs_url = f"{BASE_URL}/auth/sso/saml/acs"
    metadata = f"""<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{sp_entity_id}">
    <md:SPSSODescriptor
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol"
        AuthnRequestsSigned="false"
        WantAssertionsSigned="true">
        <md:AssertionConsumerService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="{acs_url}"
            index="0"
            isDefault="true"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""
    return HTMLResponse(content=metadata, media_type="application/xml")
