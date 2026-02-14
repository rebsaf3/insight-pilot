"""Branding service — manage workspace branding, apply to charts."""

import json
from pathlib import Path
from typing import Optional

import plotly.graph_objects as go

from config.settings import LOGOS_DIR, TIERS
from db import queries
from db.models import WorkspaceBranding


def get_branding(workspace_id: str) -> Optional[WorkspaceBranding]:
    """Get branding config for a workspace."""
    return queries.get_branding(workspace_id)


def save_branding(workspace_id: str, **kwargs) -> str:
    """Save branding settings."""
    return queries.upsert_branding(workspace_id, **kwargs)


def save_logo(workspace_id: str, logo_bytes: bytes, filename: str) -> str:
    """Save a workspace logo. Returns the relative path."""
    dir_path = LOGOS_DIR / workspace_id
    dir_path.mkdir(parents=True, exist_ok=True)

    # Keep original extension
    ext = Path(filename).suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".svg"):
        ext = ".png"

    logo_path = dir_path / f"logo{ext}"
    logo_path.write_bytes(logo_bytes)

    relative_path = f"{workspace_id}/logo{ext}"
    queries.upsert_branding(workspace_id, logo_path=relative_path)
    return relative_path


def get_logo_path(workspace_id: str) -> Optional[Path]:
    """Get the full path to the workspace logo."""
    branding = get_branding(workspace_id)
    if not branding or not branding.logo_path:
        return None
    full_path = LOGOS_DIR / branding.logo_path
    return full_path if full_path.exists() else None


def can_customize_branding(tier: str) -> tuple[bool, str]:
    """Check if branding customization is allowed for the tier."""
    tier_config = TIERS.get(tier, TIERS["free"])
    level = tier_config.get("branding_level", "none")
    if level == "none":
        return False, "Branding customization requires a Pro or Enterprise plan."
    return True, level


def apply_branding(fig: go.Figure, branding: WorkspaceBranding,
                   chart_overrides: dict = None) -> go.Figure:
    """Apply workspace branding to a plotly figure.

    Modifies: colorway, font, title styling, background, logo watermark.
    """
    if not branding:
        return fig

    overrides = chart_overrides or {}

    # Color palette
    palette = overrides.get("chart_color_palette", branding.chart_color_palette)
    if palette:
        fig.update_layout(colorway=palette)

    # Font
    font_family = overrides.get("font_family", branding.font_family)
    font_size = overrides.get("font_size_base", branding.font_size_base)
    fig.update_layout(
        font=dict(family=font_family, size=font_size),
    )

    # Background colors
    fig.update_layout(
        paper_bgcolor=overrides.get("background_color", "white"),
        plot_bgcolor=overrides.get("plot_background", "white"),
    )

    # Title styling with brand color
    primary = overrides.get("primary_color", branding.primary_color)
    if fig.layout.title and fig.layout.title.text:
        fig.update_layout(
            title_font=dict(color=primary, size=font_size + 4),
        )

    # Logo watermark (if available and not hidden)
    if not branding.hide_insightpilot_branding:
        # Add small InsightPilot text watermark
        fig.add_annotation(
            text="InsightPilot",
            xref="paper", yref="paper",
            x=1, y=-0.08,
            showarrow=False,
            font=dict(size=8, color="#ccc"),
            xanchor="right",
        )

    return fig
