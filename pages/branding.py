"""Branding page — logo, colors, fonts, chart styling."""

import streamlit as st
import plotly.express as px
import pandas as pd

from auth.session import require_permission
from services import branding_service
from config.settings import TIERS, AVAILABLE_FONTS, CHART_PALETTES


def show():
    user, ws = require_permission("manage_branding")

    st.title("Branding & Styling")

    # Tier check
    can_customize, level = branding_service.can_customize_branding(ws.tier)
    if not can_customize:
        st.warning(level)
        st.info("Upgrade to Pro or Enterprise to customize your report branding.")
        _show_preview_only()
        return

    branding = branding_service.get_branding(ws.id)

    # Tabs for different branding sections
    tab_colors, tab_fonts, tab_logo, tab_palette, tab_advanced = st.tabs(
        ["Colors", "Fonts", "Logo", "Chart Palette", "Advanced"]
    )

    with tab_colors:
        st.subheader("Brand Colors")
        col1, col2, col3 = st.columns(3)
        primary = col1.color_picker("Primary Color", value=branding.primary_color if branding else "#1E88E5")
        secondary = col2.color_picker("Secondary Color", value=branding.secondary_color if branding else "#F5F5F5")
        accent = col3.color_picker("Accent Color", value=branding.accent_color if branding else "#FF6F00")

    with tab_fonts:
        st.subheader("Report Typography")
        st.caption(
            "These font settings apply to exported reports, dashboards, and charts. "
            "They do not change the app interface font."
        )
        font_family = st.selectbox(
            "Font Family",
            AVAILABLE_FONTS,
            index=AVAILABLE_FONTS.index(branding.font_family) if branding and branding.font_family in AVAILABLE_FONTS else 0,
            help="Choose a font for your exported reports and charts",
        )
        font_size = st.slider("Base Font Size", 10, 20, value=branding.font_size_base if branding else 14)

        # Live font preview card
        st.markdown("#### Preview")
        st.markdown(
            f"<div class='ip-card' style='padding:1.5rem'>"
            f"<div style='font-family:{font_family},sans-serif;font-size:{font_size + 6}px;"
            f"font-weight:700;color:#1C1917;margin-bottom:0.5rem'>Report Heading</div>"
            f"<div style='font-family:{font_family},sans-serif;font-size:{font_size}px;"
            f"color:#57534E;line-height:1.6;margin-bottom:0.75rem'>"
            f"This is how body text will appear in your exported reports. "
            f"The quick brown fox jumps over the lazy dog.</div>"
            f"<div style='font-family:{font_family},sans-serif;font-size:{font_size}px;"
            f"color:#1C1917;font-weight:600'>Revenue: $1,234,567.89 &nbsp; | &nbsp; "
            f"Growth: +12.3% &nbsp; | &nbsp; Users: 8,421</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with tab_logo:
        st.subheader("Logo")
        logo_file = st.file_uploader("Upload Logo", type=["png", "jpg", "jpeg", "svg"])
        if logo_file:
            st.image(logo_file, width=200)

        if branding and branding.logo_path:
            logo_path = branding_service.get_logo_path(ws.id)
            if logo_path:
                st.caption("Current logo:")
                st.image(str(logo_path), width=150)

    with tab_palette:
        st.subheader("Chart Color Palette")
        palette_name = st.selectbox("Choose Palette", list(CHART_PALETTES.keys()))
        palette = CHART_PALETTES[palette_name]

        # Show palette preview
        cols = st.columns(len(palette))
        for i, (col, color) in enumerate(zip(cols, palette)):
            col.markdown(f'<div style="background:{color};width:100%;height:40px;border-radius:4px"></div>', unsafe_allow_html=True)
            col.caption(color)

    with tab_advanced:
        st.subheader("Report Header & Footer")
        header_text = st.text_input("Header Text", value=branding.header_text if branding else "")
        footer_text = st.text_input("Footer Text", value=branding.footer_text if branding else "")

        if level == "full":
            st.subheader("White Label")
            hide_branding = st.checkbox(
                "Hide InsightPilot branding on reports",
                value=branding.hide_insightpilot_branding if branding else False,
            )
        else:
            hide_branding = False
            st.info("White-label branding is available on the Enterprise plan.")

    # Save button
    st.divider()
    if st.button("Save Branding", type="primary", use_container_width=True):
        branding_service.save_branding(
            ws.id,
            primary_color=primary,
            secondary_color=secondary,
            accent_color=accent,
            font_family=font_family,
            font_size_base=font_size,
            chart_color_palette=palette,
            header_text=header_text,
            footer_text=footer_text,
            hide_insightpilot_branding=1 if hide_branding else 0,
        )

        if logo_file:
            branding_service.save_logo(ws.id, logo_file.getvalue(), logo_file.name)

        st.success("Branding saved!")
        st.rerun()

    # Live preview
    st.divider()
    st.subheader("Preview")
    _show_branded_preview(primary, accent, palette, font_family, font_size)


def _show_branded_preview(primary, accent, palette, font_family, font_size):
    """Show a sample chart with the current branding applied."""
    sample_data = pd.DataFrame({
        "Category": ["A", "B", "C", "D", "E"],
        "Value": [23, 45, 67, 34, 56],
    })

    fig = px.bar(
        sample_data, x="Category", y="Value",
        title="Sample Chart Preview",
        color="Category",
        color_discrete_sequence=palette if isinstance(palette, list) else CHART_PALETTES.get(palette, CHART_PALETTES["default"]),
    )
    fig.update_layout(
        font=dict(family=font_family, size=font_size),
        title_font=dict(color=primary, size=font_size + 4),
    )
    st.plotly_chart(fig, use_container_width=True)


def _show_preview_only():
    """Show branding preview for free tier users (read-only)."""
    st.subheader("Preview — Default Theme")
    _show_branded_preview("#1E88E5", "#FF6F00", CHART_PALETTES["default"], "Inter", 14)


show()
