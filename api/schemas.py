"""Pydantic request/response models for the REST API."""

from pydantic import BaseModel
from typing import Optional


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    """Request model for creating a new project."""
    name: str = "Q4 Sales Analysis"
    description: str = "Analysis of Q4 2025 sales data"
    instructions: str = "Always use blue color scheme. Revenue is in EUR."


class ProjectResponse(BaseModel):
    """Response model for a project."""
    id: str = "proj_123abc"
    workspace_id: str = "ws_456def"
    name: str = "Q4 Sales Analysis"
    description: str = "Analysis of Q4 2025 sales data"
    instructions: str = "Always use blue color scheme. Revenue is in EUR."
    created_at: str = "2026-02-20T12:00:00Z"


class ProjectUpdate(BaseModel):
    """Request model for updating a project."""
    name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None


# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

class PromptTemplateCreate(BaseModel):
    """Request model for creating a prompt template."""
    name: str = "Summary Prompt"
    prompt_text: str = "Summarize the uploaded data."
    category: str = "summary"


class PromptTemplateUpdate(BaseModel):
    """Request model for updating a prompt template."""
    name: Optional[str] = None
    prompt_text: Optional[str] = None
    category: Optional[str] = None


class PromptTemplateResponse(BaseModel):
    """Response model for a prompt template."""
    id: str = "tmpl_789ghi"
    project_id: str = "proj_123abc"
    name: str = "Summary Prompt"
    prompt_text: str = "Summarize the uploaded data."
    category: str = "summary"
    usage_count: int = 0
    created_at: str = "2026-02-20T12:00:00Z"


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

class FileResponse(BaseModel):
    """Response model for a file."""
    id: str = "file_abc123"
    project_id: str = "proj_123abc"
    original_filename: str = "sales_q4.csv"
    file_format: str = "csv"
    file_size_bytes: int = 20480
    row_count: Optional[int] = 1000
    column_count: Optional[int] = 12
    column_names: Optional[list[str]] = ["Date", "Revenue", "Region"]
    uploaded_at: str = "2026-02-20T12:00:00Z"


# ---------------------------------------------------------------------------
# Dashboards
# ---------------------------------------------------------------------------

class DashboardCreate(BaseModel):
    """Request model for creating a dashboard."""
    name: str = "Q4 Dashboard"
    description: str = "Main dashboard for Q4 sales."


class DashboardResponse(BaseModel):
    """Response model for a dashboard."""
    id: str = "dash_abc123"
    project_id: str = "proj_123abc"
    name: str = "Q4 Dashboard"
    description: str = "Main dashboard for Q4 sales."
    created_at: str = "2026-02-20T12:00:00Z"


class ChartResponse(BaseModel):
    """Response model for a chart."""
    id: str = "chart_abc123"
    title: str = "Sales by Region"
    chart_type: Optional[str] = "bar"
    user_prompt: str = "Show sales by region as a bar chart."
    position_index: int = 1
    created_at: str = "2026-02-20T12:00:00Z"


class DashboardDetailResponse(BaseModel):
    """Detailed response model for a dashboard, including charts."""
    id: str = "dash_abc123"
    project_id: str = "proj_123abc"
    name: str = "Q4 Dashboard"
    description: str = "Main dashboard for Q4 sales."
    charts: list[ChartResponse] = []
    created_at: str = "2026-02-20T12:00:00Z"


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

class AnalysisRequest(BaseModel):
    """Request model for AI analysis."""
    file_id: str = "file_abc123"
    prompt: str = "Create a bar chart of sales by region."
    dashboard_id: Optional[str] = None
    chart_title: Optional[str] = None


class AnalysisResponse(BaseModel):
    """Response model for AI analysis."""
    success: bool = True
    chart_id: Optional[str] = "chart_abc123"
    explanation: Optional[str] = "Bar chart of sales by region."
    credits_used: int = 10
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

class WorkspaceInfoResponse(BaseModel):
    """Response model for workspace info."""
    id: str = "ws_456def"
    name: str = "Acme Corp"
    tier: str = "Pro"
    credit_balance: int = 1000
    member_count: int = 5


class UsageResponse(BaseModel):
    """Response model for workspace usage stats."""
    credits_remaining: int = 1000
    monthly_allowance: int = 2000
    uploads_today: int = 2
    uploads_limit: int = 10
    dashboards_count: int = 3
    dashboards_limit: int = 10
    tier: str = "Pro"
