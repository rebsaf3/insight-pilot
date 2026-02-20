"""
GDPR/CCPA endpoints for user data export and deletion.
"""
from fastapi import APIRouter, Depends, HTTPException
from api.auth import get_api_key
from db import queries

router = APIRouter()

@router.get("/gdpr/export")
def export_user_data(api_key = Depends(get_api_key)):
    """Export all user data (projects, files, dashboards, etc)."""
    user_id = api_key.created_by
    # Collect user data (simplified example)
    user = queries.get_user_by_id(user_id)
    projects = queries.get_projects_for_workspace(user_id)
    # Add more as needed
    return {
        "user": user.__dict__ if user else {},
        "projects": [p.__dict__ for p in projects],
    }

@router.delete("/gdpr/delete")
def delete_user_data(api_key = Depends(get_api_key)):
    """Delete all user data and mark account for deletion."""
    user_id = api_key.created_by
    user = queries.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Delete user and related data (simplified)
    queries.delete_user(user_id)
    return {"status": "deleted"}
