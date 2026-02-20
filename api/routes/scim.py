"""
SCIM 2.0 endpoints for enterprise user/group provisioning.
This is a stub for future implementation.
"""
from fastapi import APIRouter, Request, Response

router = APIRouter()

@router.get("/scim/v2/ServiceProviderConfig")
def service_provider_config():
    """Return SCIM service provider configuration."""
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "patch": {"supported": True},
        "bulk": {"supported": False},
        "filter": {"supported": True, "maxResults": 200},
        "changePassword": {"supported": False},
        "sort": {"supported": True},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {"type": "oauthbearer", "name": "OAuth Bearer Token", "description": "Authentication using OAuth Bearer Token", "primary": True}
        ]
    }

@router.get("/scim/v2/Users")
def list_users():
    """List users (stub)."""
    return {"Resources": [], "totalResults": 0, "itemsPerPage": 0, "startIndex": 1}

@router.get("/scim/v2/Groups")
def list_groups():
    """List groups (stub)."""
    return {"Resources": [], "totalResults": 0, "itemsPerPage": 0, "startIndex": 1}
