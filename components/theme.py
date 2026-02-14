"""Custom CSS theme injection — matches the Joyful Innovation design system.

Call ``inject_custom_css()`` once at the top of the main app entrypoint to
apply global styling overrides on top of the Streamlit theme defined in
``.streamlit/config.toml``.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Design tokens — derived from joyfulinnovation.com
# ---------------------------------------------------------------------------
PRIMARY = "#2D3FE0"          # Royal blue — buttons, links, accents
PRIMARY_HOVER = "#1E2FC0"    # Darker blue on hover
PRIMARY_LIGHT = "#EEF0FC"    # Very light blue tint
SURFACE = "#FFFFFF"          # Card / panel backgrounds
BG_SECTION = "#F4F6FA"       # Section backgrounds, sidebar
TEXT_PRIMARY = "#111827"      # Headings, body text
TEXT_SECONDARY = "#6B7280"   # Captions, muted text
TEXT_TERTIARY = "#9CA3AF"    # Placeholders, disabled
BORDER = "#E5E7EB"           # Card borders, dividers
BORDER_LIGHT = "#F3F4F6"     # Subtle separators
SUCCESS = "#059669"          # Green accents
ERROR = "#DC2626"            # Red error states
RADIUS = "10px"              # Card / button border-radius
RADIUS_SM = "6px"            # Small elements
SHADOW_SM = "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)"
SHADOW_MD = "0 4px 12px rgba(0,0,0,0.06), 0 2px 4px rgba(0,0,0,0.04)"
FONT_STACK = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"


def inject_custom_css() -> None:
    """Inject the full custom CSS stylesheet into the Streamlit app.

    Call once from the entrypoint file (app.py). The <link> tag for Google
    Fonts is injected separately from the <style> block because @import
    rules inside dynamically injected <style> elements are unreliable in
    some browsers.
    """
    st.markdown(_FONT_LINK + _CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Google Fonts — loaded via <link> tag (reliable across all browsers)
# ---------------------------------------------------------------------------
_FONT_LINK = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
"""

# ---------------------------------------------------------------------------
# Master stylesheet
# ---------------------------------------------------------------------------
_CSS = f"""
<style>
/* ====================================================================
   InsightPilot — Custom Theme (Joyful Innovation design system)
   ==================================================================== */

/* --- Root / body --------------------------------------------------- */
html, body, [data-testid="stApp"] {{
    font-family: {FONT_STACK} !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}}

/* --- Headings ------------------------------------------------------ */
h1, h2, h3, h4, h5, h6,
[data-testid="stHeadingWithActionElements"] {{
    font-family: {FONT_STACK} !important;
    color: {TEXT_PRIMARY} !important;
    font-weight: 700 !important;
    letter-spacing: -0.025em;
}}

h1 {{ font-size: 2rem !important; }}
h2 {{ font-size: 1.5rem !important; }}
h3 {{ font-size: 1.25rem !important; }}

/* --- Body text ----------------------------------------------------- */
p, li, span, label, div {{
    font-family: {FONT_STACK} !important;
}}

/* --- Sidebar ------------------------------------------------------- */
section[data-testid="stSidebar"] {{
    background-color: {BG_SECTION} !important;
    border-right: 1px solid {BORDER} !important;
}}

section[data-testid="stSidebar"] .stMarkdown {{
    color: {TEXT_PRIMARY} !important;
}}

/* --- Primary buttons ----------------------------------------------- */
button[data-testid="stBaseButton-primary"],
button[kind="primary"] {{
    background-color: {PRIMARY} !important;
    color: white !important;
    border: none !important;
    border-radius: {RADIUS_SM} !important;
    font-weight: 600 !important;
    font-family: {FONT_STACK} !important;
    letter-spacing: 0.01em;
    padding: 0.5rem 1.25rem !important;
    transition: background-color 0.15s ease, box-shadow 0.15s ease !important;
}}

button[data-testid="stBaseButton-primary"]:hover,
button[kind="primary"]:hover {{
    background-color: {PRIMARY_HOVER} !important;
    box-shadow: {SHADOW_SM} !important;
}}

/* --- Secondary / outline buttons ----------------------------------- */
button[data-testid="stBaseButton-secondary"],
button[kind="secondary"] {{
    background-color: {SURFACE} !important;
    color: {TEXT_PRIMARY} !important;
    border: 1px solid {BORDER} !important;
    border-radius: {RADIUS_SM} !important;
    font-weight: 500 !important;
    font-family: {FONT_STACK} !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}}

button[data-testid="stBaseButton-secondary"]:hover,
button[kind="secondary"]:hover {{
    border-color: {PRIMARY} !important;
    color: {PRIMARY} !important;
    box-shadow: {SHADOW_SM} !important;
}}

/* --- Form submit buttons ------------------------------------------- */
button[type="submit"] {{
    border-radius: {RADIUS_SM} !important;
    font-weight: 600 !important;
    font-family: {FONT_STACK} !important;
}}

/* --- Link buttons -------------------------------------------------- */
a[data-testid="stBaseButton-secondary"] {{
    border-radius: {RADIUS_SM} !important;
}}

/* --- Text inputs / text areas -------------------------------------- */
input[type="text"],
input[type="password"],
input[type="email"],
input[type="number"],
textarea,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {{
    border: 1px solid {BORDER} !important;
    border-radius: {RADIUS_SM} !important;
    font-family: {FONT_STACK} !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}}

input:focus,
textarea:focus {{
    border-color: {PRIMARY} !important;
    box-shadow: 0 0 0 3px {PRIMARY_LIGHT} !important;
}}

/* --- Select boxes -------------------------------------------------- */
[data-testid="stSelectbox"] > div > div {{
    border-radius: {RADIUS_SM} !important;
    border-color: {BORDER} !important;
}}

/* --- Metric cards -------------------------------------------------- */
[data-testid="stMetric"] {{
    background-color: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: {RADIUS} !important;
    padding: 1rem !important;
    box-shadow: {SHADOW_SM} !important;
}}

[data-testid="stMetricLabel"] {{
    color: {TEXT_SECONDARY} !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}}

[data-testid="stMetricValue"] {{
    color: {TEXT_PRIMARY} !important;
    font-weight: 700 !important;
}}

/* --- Expanders ----------------------------------------------------- */
[data-testid="stExpander"] {{
    border: 1px solid {BORDER} !important;
    border-radius: {RADIUS} !important;
    overflow: hidden;
}}

[data-testid="stExpander"] summary {{
    font-weight: 600 !important;
    font-family: {FONT_STACK} !important;
}}

/* --- Tabs ---------------------------------------------------------- */
button[data-baseweb="tab"] {{
    font-family: {FONT_STACK} !important;
    font-weight: 500 !important;
    color: {TEXT_SECONDARY} !important;
    border-bottom: 2px solid transparent !important;
    transition: color 0.15s ease !important;
}}

button[data-baseweb="tab"][aria-selected="true"] {{
    color: {PRIMARY} !important;
    border-bottom-color: {PRIMARY} !important;
    font-weight: 600 !important;
}}

button[data-baseweb="tab"]:hover {{
    color: {PRIMARY} !important;
}}

/* --- Dividers ------------------------------------------------------ */
hr {{
    border-color: {BORDER_LIGHT} !important;
}}

/* --- Alert / info boxes -------------------------------------------- */
[data-testid="stAlert"] {{
    border-radius: {RADIUS_SM} !important;
    font-family: {FONT_STACK} !important;
}}

/* --- Data tables --------------------------------------------------- */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER} !important;
    border-radius: {RADIUS} !important;
    overflow: hidden;
}}

/* --- File uploader ------------------------------------------------- */
[data-testid="stFileUploader"] {{
    border-radius: {RADIUS} !important;
}}

/* --- Plotly charts — override background to match theme ------------ */
.js-plotly-plot .plotly {{
    border-radius: {RADIUS} !important;
}}

/* --- Navigation / page links --------------------------------------- */
[data-testid="stSidebarNav"] a {{
    font-family: {FONT_STACK} !important;
    font-weight: 500 !important;
    border-radius: {RADIUS_SM} !important;
    transition: background-color 0.15s ease !important;
}}

[data-testid="stSidebarNav"] a:hover {{
    background-color: {PRIMARY_LIGHT} !important;
}}

/* --- Progress bars ------------------------------------------------- */
[data-testid="stProgress"] > div > div {{
    background-color: {PRIMARY} !important;
    border-radius: 999px !important;
}}

/* --- Captions ------------------------------------------------------ */
[data-testid="stCaptionContainer"] {{
    color: {TEXT_SECONDARY} !important;
}}

/* --- Container borders (forms, etc.) ------------------------------- */
[data-testid="stForm"] {{
    border: 1px solid {BORDER} !important;
    border-radius: {RADIUS} !important;
    padding: 1.5rem !important;
}}

/* --- Toast / success messages -------------------------------------- */
[data-testid="stToast"] {{
    border-radius: {RADIUS_SM} !important;
}}

/* --- Hide Streamlit branding --------------------------------------- */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}

</style>
"""
