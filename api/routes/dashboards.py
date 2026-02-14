"""REST API routes for dashboard CRUD."""

from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_api_key, get_workspace_from_key, require_permission
from api.schemas import DashboardCreate, DashboardResponse, DashboardDetailResponse, ChartResponse
from db import queries
from db.models import ApiKey, Workspace

router = APIRouter()


@router.get("/projects/{project_id}/dashboards", response_model=list[DashboardResponse])
async def list_dashboards(project_id: str, ws: Workspace = Depends(get_workspace_from_key)):
    project = queries.get_project_by_id(project_id, ws.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    dashboards = queries.get_dashboards_for_project(project_id)
    return [DashboardResponse(
        id=d.id, project_id=d.project_id, name=d.name,
        description=d.description, created_at=d.created_at,
    ) for d in dashboards]


@router.post("/projects/{project_id}/dashboards", response_model=DashboardResponse)
async def create_dashboard(
    project_id: str,
    body: DashboardCreate,
    api_key: ApiKey = Depends(require_permission("write")),
    ws: Workspace = Depends(get_workspace_from_key),
):
    project = queries.get_project_by_id(project_id, ws.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    did = queries.create_dashboard(
        project_id=project_id,
        created_by=api_key.created_by,
        name=body.name,
        description=body.description,
    )
    dashboard = queries.get_dashboard_by_id(did)
    return DashboardResponse(
        id=dashboard.id, project_id=dashboard.project_id, name=dashboard.name,
        description=dashboard.description, created_at=dashboard.created_at,
    )


@router.get("/dashboards/{dashboard_id}", response_model=DashboardDetailResponse)
async def get_dashboard(dashboard_id: str, ws: Workspace = Depends(get_workspace_from_key)):
    dashboard = queries.get_dashboard_by_id(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    charts = queries.get_charts_for_dashboard(dashboard_id)
    return DashboardDetailResponse(
        id=dashboard.id, project_id=dashboard.project_id, name=dashboard.name,
        description=dashboard.description, created_at=dashboard.created_at,
        charts=[ChartResponse(
            id=c.id, title=c.title, chart_type=c.chart_type,
            user_prompt=c.user_prompt, position_index=c.position_index,
            created_at=c.created_at,
        ) for c in charts],
    )


@router.delete("/dashboards/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: str,
    api_key: ApiKey = Depends(require_permission("write")),
    ws: Workspace = Depends(get_workspace_from_key),
):
    dashboard = queries.get_dashboard_by_id(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    queries.delete_dashboard(dashboard_id)
    return {"status": "deleted"}
