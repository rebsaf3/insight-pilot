"""REST API routes for project CRUD and prompt templates."""

from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_api_key, get_workspace_from_key, require_permission
from api.schemas import (
    ProjectCreate, ProjectResponse, ProjectUpdate,
    PromptTemplateCreate, PromptTemplateUpdate, PromptTemplateResponse,
)
from db import queries
from db.models import ApiKey, Workspace

router = APIRouter()


def _project_response(p) -> ProjectResponse:
    return ProjectResponse(
        id=p.id, workspace_id=p.workspace_id, name=p.name,
        description=p.description, instructions=p.instructions,
        created_at=p.created_at,
    )


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(ws: Workspace = Depends(get_workspace_from_key)):
    projects = queries.get_projects_for_workspace(ws.id)
    return [_project_response(p) for p in projects]


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
        instructions=body.instructions,
    )
    project = queries.get_project_by_id(pid, ws.id)
    return _project_response(project)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, ws: Workspace = Depends(get_workspace_from_key)):
    project = queries.get_project_by_id(project_id, ws.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_response(project)


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
    return _project_response(project)


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


# =========================================================================
# Prompt Templates (nested under projects)
# =========================================================================

@router.get("/projects/{project_id}/templates", response_model=list[PromptTemplateResponse])
async def list_templates(
    project_id: str,
    ws: Workspace = Depends(get_workspace_from_key),
):
    project = queries.get_project_by_id(project_id, ws.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    templates = queries.get_prompt_templates_for_project(project_id)
    return [PromptTemplateResponse(
        id=t.id, project_id=t.project_id, name=t.name,
        prompt_text=t.prompt_text, category=t.category,
        usage_count=t.usage_count, created_at=t.created_at,
    ) for t in templates]


@router.post("/projects/{project_id}/templates", response_model=PromptTemplateResponse)
async def create_template(
    project_id: str,
    body: PromptTemplateCreate,
    api_key: ApiKey = Depends(require_permission("write")),
    ws: Workspace = Depends(get_workspace_from_key),
):
    project = queries.get_project_by_id(project_id, ws.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tid = queries.create_prompt_template(
        project_id=project_id,
        created_by=api_key.created_by,
        name=body.name,
        prompt_text=body.prompt_text,
        category=body.category,
    )
    t = queries.get_prompt_template_by_id(tid)
    return PromptTemplateResponse(
        id=t.id, project_id=t.project_id, name=t.name,
        prompt_text=t.prompt_text, category=t.category,
        usage_count=t.usage_count, created_at=t.created_at,
    )


@router.put("/projects/{project_id}/templates/{template_id}", response_model=PromptTemplateResponse)
async def update_template(
    project_id: str,
    template_id: str,
    body: PromptTemplateUpdate,
    api_key: ApiKey = Depends(require_permission("write")),
    ws: Workspace = Depends(get_workspace_from_key),
):
    project = queries.get_project_by_id(project_id, ws.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    t = queries.get_prompt_template_by_id(template_id)
    if not t or t.project_id != project_id:
        raise HTTPException(status_code=404, detail="Template not found")
    updates = body.model_dump(exclude_none=True)
    if updates:
        queries.update_prompt_template(template_id, **updates)
    t = queries.get_prompt_template_by_id(template_id)
    return PromptTemplateResponse(
        id=t.id, project_id=t.project_id, name=t.name,
        prompt_text=t.prompt_text, category=t.category,
        usage_count=t.usage_count, created_at=t.created_at,
    )


@router.delete("/projects/{project_id}/templates/{template_id}")
async def delete_template(
    project_id: str,
    template_id: str,
    api_key: ApiKey = Depends(require_permission("write")),
    ws: Workspace = Depends(get_workspace_from_key),
):
    project = queries.get_project_by_id(project_id, ws.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    t = queries.get_prompt_template_by_id(template_id)
    if not t or t.project_id != project_id:
        raise HTTPException(status_code=404, detail="Template not found")
    queries.delete_prompt_template(template_id)
    return {"status": "deleted"}
