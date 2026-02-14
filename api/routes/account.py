"""REST API routes for account/workspace info."""

from fastapi import APIRouter, Depends

from api.auth import get_api_key, get_workspace_from_key
from api.schemas import WorkspaceInfoResponse, UsageResponse
from db import queries
from db.models import ApiKey, Workspace
from services import credit_service

router = APIRouter()


@router.get("/workspace", response_model=WorkspaceInfoResponse)
async def get_workspace_info(
    api_key: ApiKey = Depends(get_api_key),
    ws: Workspace = Depends(get_workspace_from_key),
):
    balance = credit_service.get_balance(ws.id)
    member_count = queries.count_workspace_members(ws.id)
    return WorkspaceInfoResponse(
        id=ws.id,
        name=ws.name,
        tier=ws.tier,
        credit_balance=balance,
        member_count=member_count,
    )


@router.get("/workspace/usage", response_model=UsageResponse)
async def get_usage(
    api_key: ApiKey = Depends(get_api_key),
    ws: Workspace = Depends(get_workspace_from_key),
):
    usage = credit_service.get_usage_summary(ws.id, api_key.created_by)
    return UsageResponse(**usage)
