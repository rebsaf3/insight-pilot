"""Central configuration for InsightPilot. Loads .env and defines constants."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
# PERSIST_DIR holds all mutable data (DB + uploads). On Railway this is a
# mounted volume (/app/data); locally it defaults to <project>/data.
PERSIST_DIR = Path(os.getenv("PERSIST_DIR", str(BASE_DIR / "data")))
DB_PATH = PERSIST_DIR / "insight_pilot.db"
STORAGE_DIR = PERSIST_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
LOGOS_DIR = STORAGE_DIR / "logos"
EXPORTS_DIR = STORAGE_DIR / "exports"

# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEFAULT_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "4096"))

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
APP_TITLE = "InsightPilot"
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "change-me-in-production")
SESSION_EXPIRY_DAYS = 30

# ---------------------------------------------------------------------------
# File upload
# ---------------------------------------------------------------------------
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "200"))
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}

# ---------------------------------------------------------------------------
# Code execution
# ---------------------------------------------------------------------------
CODE_EXEC_TIMEOUT_SECONDS = int(os.getenv("CODE_EXEC_TIMEOUT", "30"))

# ---------------------------------------------------------------------------
# Encryption (for TOTP secrets at rest)
# ---------------------------------------------------------------------------
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# ---------------------------------------------------------------------------
# Email / SMTP
# ---------------------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "InsightPilot")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@insightpilot.com")

# ---------------------------------------------------------------------------
# Stripe
# ---------------------------------------------------------------------------
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID", "")
STRIPE_ENTERPRISE_PRICE_ID = os.getenv("STRIPE_ENTERPRISE_PRICE_ID", "")
STRIPE_API_ADDON_PRICE_ID = os.getenv("STRIPE_API_ADDON_PRICE_ID", "")
STRIPE_TOPUP_PRICE_ID = os.getenv("STRIPE_TOPUP_PRICE_ID", "")

# ---------------------------------------------------------------------------
# SSO
# ---------------------------------------------------------------------------
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
MICROSOFT_TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "")

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
API_SERVER_PORT = int(os.getenv("API_SERVER_PORT", "8100"))
BASE_URL = os.getenv("BASE_URL", "http://localhost:8100")

# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------
TIERS = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "monthly_credits": 50,
        "uploads_per_day": 1,
        "max_file_size_mb": 10,
        "max_revisions_per_report": 0,
        "max_dashboards": 3,
        "export_enabled": False,
        "topup_enabled": False,
        "max_members": 1,
        "tfa_required": False,
        "sso_providers": [],
        "branding_level": "none",       # none | basic | full
        "api_addon_available": False,
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 29,
        "monthly_credits": 500,
        "uploads_per_day": 10,
        "max_file_size_mb": 100,
        "max_revisions_per_report": -1,  # unlimited
        "max_dashboards": 25,
        "export_enabled": True,
        "topup_enabled": True,
        "max_members": 10,
        "tfa_required": False,
        "sso_providers": ["google", "microsoft"],
        "branding_level": "basic",
        "api_addon_available": True,
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 99,
        "monthly_credits": 2000,
        "uploads_per_day": -1,           # unlimited
        "max_file_size_mb": 500,
        "max_revisions_per_report": -1,
        "max_dashboards": -1,
        "export_enabled": True,
        "topup_enabled": True,
        "max_members": -1,
        "tfa_required": True,
        "sso_providers": ["google", "microsoft", "saml"],
        "branding_level": "full",
        "api_addon_available": True,
    },
}

# ---------------------------------------------------------------------------
# Role permissions
# ---------------------------------------------------------------------------
ROLE_PERMISSIONS = {
    "owner": {
        "view_dashboards", "export_dashboards", "upload_data", "run_analysis",
        "create_edit_dashboards", "create_delete_projects", "invite_remove_members",
        "change_member_roles", "manage_billing", "delete_workspace",
        "transfer_ownership", "manage_branding", "manage_sso", "manage_api_keys",
    },
    "admin": {
        "view_dashboards", "export_dashboards", "upload_data", "run_analysis",
        "create_edit_dashboards", "create_delete_projects", "invite_remove_members",
        "change_member_roles", "manage_branding", "manage_api_keys",
    },
    "member": {
        "view_dashboards", "export_dashboards", "upload_data", "run_analysis",
        "create_edit_dashboards", "create_delete_projects",
    },
    "viewer": {
        "view_dashboards", "export_dashboards",
    },
}

# ---------------------------------------------------------------------------
# Credit pricing
# ---------------------------------------------------------------------------
TOKENS_PER_CREDIT = 1000
TOPUP_CREDITS = 100
TOPUP_PRICE_CENTS = 1000  # $10.00

# ---------------------------------------------------------------------------
# Branding font options (Pro tier)
# ---------------------------------------------------------------------------
AVAILABLE_FONTS = [
    "Inter", "Roboto", "Open Sans", "Lato", "Montserrat",
    "Source Sans Pro", "Nunito", "Poppins", "Raleway", "PT Sans",
]

# ---------------------------------------------------------------------------
# Admin / Superadmin
# ---------------------------------------------------------------------------
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")

CHART_PALETTES = {
    "default": ["#2D3FE0", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"],
    "pastel": ["#a1c9f4", "#ffb482", "#8de5a1", "#ff9f9b", "#d0bbff", "#debb9b"],
    "vibrant": ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231", "#911eb4"],
    "cool": ["#264653", "#2a9d8f", "#e9c46a", "#f4a261", "#e76f51", "#606c38"],
    "warm": ["#d00000", "#e85d04", "#faa307", "#ffba08", "#dc2f02", "#9d0208"],
    "ocean": ["#03045e", "#0077b6", "#00b4d8", "#90e0ef", "#caf0f8", "#023e8a"],
    "earth": ["#606c38", "#283618", "#fefae0", "#dda15e", "#bc6c25", "#3a5a40"],
    "mono": ["#212529", "#495057", "#6c757d", "#adb5bd", "#dee2e6", "#f8f9fa"],
}
