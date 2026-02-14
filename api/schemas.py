"""Pydantic request/response models for the REST API."""

from pydantic import BaseModel
from typing import Optional


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    instructions: str = ""


class ProjectResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str
    instructions: str = ""
    created_at: str


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None


# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

class PromptTemplateCreate(BaseModel):
    name: str
    prompt_text: str
    category: str = ""


class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    prompt_text: Optional[str] = None
    category: Optional[str] = None


class PromptTemplateResponse(BaseModel):
    id: str
    project_id: str
    name: str
    prompt_text: str
    category: str = ""
    usage_count: int = 0
    created_at: str


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

class FileResponse(BaseModel):
    id: str
    project_id: str
    original_filename: str
    file_format: str
    file_size_bytes: int
    row_count: Optional[int]
    column_count: Optional[int]
    column_names: Optional[list[str]]
    uploaded_at: str


# ---------------------------------------------------------------------------
# Dashboards
# ---------------------------------------------------------------------------

class DashboardCreate(BaseModel):
    name: str
    description: str = ""


class DashboardResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: str
    created_at: str


class ChartResponse(BaseModel):
    id: str
    title: str
    chart_type: Optional[str]
    user_prompt: str
    position_index: int
    created_at: str


class DashboardDetailResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: str
    charts: list[ChartResponse]
    created_at: str


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

class AnalysisRequest(BaseModel):
    file_id: str
    prompt: str
    dashboard_id: Optional[str] = None
    chart_title: Optional[str] = None


class AnalysisResponse(BaseModel):
    success: bool
    chart_id: Optional[str] = None
    explanation: Optional[str] = None
    credits_used: int = 0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

class WorkspaceInfoResponse(BaseModel):
    id: str
    name: str
    tier: str
    credit_balance: int
    member_count: int


class UsageResponse(BaseModel):
    credits_remaining: int
    monthly_allowance: int
    uploads_today: int
    uploads_limit: int
    dashboards_count: int
    dashboards_limit: int
    tier: str
