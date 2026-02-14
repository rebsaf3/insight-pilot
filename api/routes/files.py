"""REST API routes for file upload and management."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from api.auth import get_api_key, get_workspace_from_key, require_permission
from api.schemas import FileResponse
from db import queries
from db.models import ApiKey, Workspace
from services import file_service, data_profiler, credit_service

router = APIRouter()


@router.get("/projects/{project_id}/files", response_model=list[FileResponse])
async def list_files(project_id: str, ws: Workspace = Depends(get_workspace_from_key)):
    project = queries.get_project_by_id(project_id, ws.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    files = queries.get_files_for_project(project_id)
    return [FileResponse(
        id=f.id, project_id=f.project_id, original_filename=f.original_filename,
        file_format=f.file_format, file_size_bytes=f.file_size_bytes,
        row_count=f.row_count, column_count=f.column_count,
        column_names=f.column_names, uploaded_at=f.uploaded_at,
    ) for f in files]


@router.post("/projects/{project_id}/upload", response_model=FileResponse)
async def upload_file(
    project_id: str,
    file: UploadFile = File(...),
    api_key: ApiKey = Depends(require_permission("write")),
    ws: Workspace = Depends(get_workspace_from_key),
):
    project = queries.get_project_by_id(project_id, ws.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Read file content
    content = await file.read()

    # Validate
    allowed, msg = credit_service.check_upload_allowed(api_key.created_by, ws.id)
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    size_ok, size_msg = credit_service.check_file_size_allowed(ws.id, len(content))
    if not size_ok:
        raise HTTPException(status_code=413, detail=size_msg)

    file_format = file_service.detect_format(file.filename)
    if file_format == "unknown":
        raise HTTPException(status_code=400, detail="Unsupported file format")

    # Save
    stored_filename, file_path = file_service.save_uploaded_file(
        content, file.filename, ws.id, project_id,
    )

    file_id = queries.create_uploaded_file(
        project_id=project_id,
        uploaded_by=api_key.created_by,
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_format=file_format,
        file_size_bytes=len(content),
    )

    # Profile
    try:
        df = file_service.load_dataframe(file_path, file_format)
        profile = data_profiler.profile_dataframe(df)
        queries.update_file_profile(
            file_id=file_id,
            row_count=profile["row_count"],
            column_count=profile["column_count"],
            column_names=list(df.columns),
            data_profile=profile,
        )
    except Exception:
        pass  # File saved but profiling failed — not critical

    uploaded_file = queries.get_file_by_id(file_id)
    return FileResponse(
        id=uploaded_file.id, project_id=uploaded_file.project_id,
        original_filename=uploaded_file.original_filename,
        file_format=uploaded_file.file_format, file_size_bytes=uploaded_file.file_size_bytes,
        row_count=uploaded_file.row_count, column_count=uploaded_file.column_count,
        column_names=uploaded_file.column_names, uploaded_at=uploaded_file.uploaded_at,
    )


@router.get("/projects/{project_id}/files/{file_id}", response_model=FileResponse)
async def get_file(project_id: str, file_id: str, ws: Workspace = Depends(get_workspace_from_key)):
    f = queries.get_file_by_id(file_id)
    if not f or f.project_id != project_id:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        id=f.id, project_id=f.project_id, original_filename=f.original_filename,
        file_format=f.file_format, file_size_bytes=f.file_size_bytes,
        row_count=f.row_count, column_count=f.column_count,
        column_names=f.column_names, uploaded_at=f.uploaded_at,
    )


@router.delete("/projects/{project_id}/files/{file_id}")
async def delete_file(
    project_id: str, file_id: str,
    api_key: ApiKey = Depends(require_permission("write")),
    ws: Workspace = Depends(get_workspace_from_key),
):
    f = queries.get_file_by_id(file_id)
    if not f or f.project_id != project_id:
        raise HTTPException(status_code=404, detail="File not found")
    file_service.delete_stored_file(f.file_path)
    queries.delete_file(file_id)
    return {"status": "deleted"}
