"""REST API routes for project CRUD."""

from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_api_key, get_workspace_from_key, require_permission
from api.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from db import queries
from db.models import ApiKey, Workspace

router = APIRouter()


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(ws: Workspace = Depends(get_workspace_from_key)):
    projects = queries.get_projects_for_workspace(ws.id)
    return [ProjectResponse(
        id=p.id, workspace_id=p.workspace_id, name=p.name,
        description=p.description, created_at=p.created_at,
    ) for p in projects]


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    body: ProjectCreate,
    api_key: ApiKey = Depends(require_permission("write")),
    ws: Workspace = Depends(get_workspace_from_key),
):
    pid = queries.create_project(
        workspace_id=ws.id,
        created_by=api_key.created_by,
        name=body.name,
        description=body.description,
    )
    project = queries.get_project_by_id(pid, ws.id)
    return ProjectResponse(
        id=project.id, workspace_id=project.workspace_id, name=project.name,
        description=project.description, created_at=project.created_at,
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, ws: Workspace = Depends(get_workspace_from_key)):
    project = queries.get_project_by_id(project_id, ws.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=project.id, workspace_id=project.workspace_id, name=project.name,
        description=project.description, created_at=project.created_at,
    )


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    api_key: ApiKey = Depends(require_permission("write")),
    ws: Workspace = Depends(get_workspace_from_key),
):
    project = queries.get_project_by_id(project_id, ws.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    updates = body.model_dump(exclude_none=True)
    if updates:
        queries.update_project(project_id, ws.id, **updates)
    project = queries.get_project_by_id(project_id, ws.id)
    return ProjectResponse(
        id=project.id, workspace_id=project.workspace_id, name=project.name,
        description=project.description, created_at=project.created_at,
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    api_key: ApiKey = Depends(require_permission("write")),
    ws: Workspace = Depends(get_workspace_from_key),
):
    project = queries.get_project_by_id(project_id, ws.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    queries.delete_project(project_id, ws.id)
    return {"status": "deleted"}
