"""Data models representing database rows as typed dataclasses."""

from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    display_name: str
    avatar_url: Optional[str]
    totp_secret: Optional[str]
    totp_enabled: bool
    email_2fa_enabled: bool
    sso_provider: Optional[str]
    sso_provider_id: Optional[str]
    is_superadmin: bool = False
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if isinstance(self.is_superadmin, int):
            self.is_superadmin = bool(self.is_superadmin)
        if isinstance(self.totp_enabled, int):
            self.totp_enabled = bool(self.totp_enabled)
        if isinstance(self.email_2fa_enabled, int):
            self.email_2fa_enabled = bool(self.email_2fa_enabled)

    @property
    def has_2fa(self) -> bool:
        return self.totp_enabled or self.email_2fa_enabled


@dataclass
class UserSession:
    id: str
    user_id: str
    session_token: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: str
    expires_at: str


@dataclass
class Workspace:
    id: str
    name: str
    description: str
    owner_id: str
    tier: str
    stripe_customer_id: Optional[str]
    sso_enabled: bool
    sso_config: Optional[dict]
    created_at: str
    updated_at: str

    def __post_init__(self):
        if isinstance(self.sso_config, str):
            self.sso_config = json.loads(self.sso_config) if self.sso_config else None
        if isinstance(self.sso_enabled, int):
            self.sso_enabled = bool(self.sso_enabled)


@dataclass
class WorkspaceMember:
    id: str
    workspace_id: str
    user_id: str
    role: str
    invited_by: Optional[str]
    joined_at: str


@dataclass
class WorkspaceInvitation:
    id: str
    workspace_id: str
    email: str
    role: str
    invited_by: str
    token: str
    status: str
    created_at: str
    expires_at: str


@dataclass
class Project:
    id: str
    workspace_id: str
    created_by: str
    name: str
    description: str
    instructions: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class UploadedFile:
    id: str
    project_id: str
    uploaded_by: str
    original_filename: str
    stored_filename: str
    file_path: str
    file_format: str
    file_size_bytes: int
    row_count: Optional[int]
    column_count: Optional[int]
    column_names: Optional[list[str]]
    data_profile: Optional[dict]
    uploaded_at: str

    def __post_init__(self):
        if isinstance(self.column_names, str):
            self.column_names = json.loads(self.column_names) if self.column_names else None
        if isinstance(self.data_profile, str):
            self.data_profile = json.loads(self.data_profile) if self.data_profile else None


@dataclass
class Dashboard:
    id: str
    project_id: str
    created_by: str
    name: str
    description: str
    layout: list
    style_config: Optional[dict]
    created_at: str
    updated_at: str

    def __post_init__(self):
        if isinstance(self.layout, str):
            self.layout = json.loads(self.layout) if self.layout else []
        if isinstance(self.style_config, str):
            self.style_config = json.loads(self.style_config) if self.style_config else None


@dataclass
class Chart:
    id: str
    dashboard_id: str
    file_id: str
    title: str
    chart_type: Optional[str]
    user_prompt: str
    generated_code: str
    plotly_json: Optional[str]
    style_overrides: Optional[dict]
    position_index: int
    created_by: str
    created_at: str
    updated_at: str

    def __post_init__(self):
        if isinstance(self.style_overrides, str):
            self.style_overrides = json.loads(self.style_overrides) if self.style_overrides else None


@dataclass
class CreditLedgerEntry:
    id: str
    workspace_id: str
    user_id: str
    change_amount: int
    balance_after: int
    reason: str
    reference_id: Optional[str]
    created_at: str


@dataclass
class Subscription:
    id: str
    workspace_id: str
    tier: str
    stripe_subscription_id: Optional[str]
    status: str
    current_period_start: Optional[str]
    current_period_end: Optional[str]
    monthly_credit_allowance: int
    created_at: str
    updated_at: str


@dataclass
class CreditPurchase:
    id: str
    workspace_id: str
    purchased_by: str
    stripe_payment_id: Optional[str]
    credits_purchased: int
    amount_paid_cents: int
    created_at: str


@dataclass
class AddOn:
    id: str
    workspace_id: str
    add_on_type: str
    stripe_subscription_id: Optional[str]
    status: str
    created_at: str
    updated_at: str


@dataclass
class WorkspaceBranding:
    id: str
    workspace_id: str
    logo_path: Optional[str]
    primary_color: str
    secondary_color: str
    accent_color: str
    font_family: str
    font_size_base: int
    chart_color_palette: list[str]
    header_text: str
    footer_text: str
    hide_insightpilot_branding: bool
    updated_at: str

    def __post_init__(self):
        if isinstance(self.chart_color_palette, str):
            self.chart_color_palette = json.loads(self.chart_color_palette)
        if isinstance(self.hide_insightpilot_branding, int):
            self.hide_insightpilot_branding = bool(self.hide_insightpilot_branding)


@dataclass
class ApiKey:
    id: str
    workspace_id: str
    created_by: str
    key_hash: str
    key_prefix: str
    name: str
    permissions: dict
    last_used_at: Optional[str]
    created_at: str
    revoked_at: Optional[str]

    def __post_init__(self):
        if isinstance(self.permissions, str):
            self.permissions = json.loads(self.permissions)


@dataclass
class PromptHistoryEntry:
    id: str
    user_id: str
    workspace_id: str
    project_id: str
    file_id: Optional[str]
    prompt_text: str
    response_code: Optional[str]
    response_error: Optional[str]
    tokens_used: int
    model_used: str
    created_at: str


@dataclass
class PromptTemplate:
    id: str
    project_id: str
    created_by: str
    name: str
    prompt_text: str
    category: str = ""
    is_default: bool = False
    usage_count: int = 0
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if isinstance(self.is_default, int):
            self.is_default = bool(self.is_default)


@dataclass
class AuditLogEntry:
    id: str
    user_id: Optional[str]
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: str = ""

    def __post_init__(self):
        if isinstance(self.details, str) and self.details:
            try:
                self.details = json.loads(self.details)
            except (json.JSONDecodeError, TypeError):
                pass


@dataclass
class SystemSetting:
    key: str
    value: str
    updated_by: Optional[str] = None
    updated_at: str = ""


# ---------------------------------------------------------------------------
# Helper to convert sqlite3.Row to a model dataclass
# ---------------------------------------------------------------------------

def row_to_model(row, model_class):
    """Convert a sqlite3.Row to a dataclass instance.
    Handles the case where row has more columns than the dataclass expects
    by only passing recognized fields."""
    if row is None:
        return None
    d = dict(row)
    # Only pass keys that the dataclass accepts
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(model_class)}
    filtered = {k: v for k, v in d.items() if k in field_names}
    return model_class(**filtered)


def rows_to_models(rows, model_class):
    """Convert a list of sqlite3.Row to a list of dataclass instances."""
    return [row_to_model(r, model_class) for r in rows]
