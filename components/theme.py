"""Custom CSS theme injection — matches the Joyful Innovation design system.

Call ``inject_custom_css()`` once at the top of the main app entrypoint to
apply global styling overrides on top of the Streamlit theme defined in
``.streamlit/config.toml``.

Design language: warm, airy, human — soft cream backgrounds, teal/green
accents, generous whitespace, refined typography, subtle card borders.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Design tokens — derived from joyfulinnovation.com
# ---------------------------------------------------------------------------
# Primary brand colors
PRIMARY = "#0F766E"              # Teal — primary buttons, links, accents
PRIMARY_HOVER = "#0D6660"        # Darker teal on hover
PRIMARY_LIGHT = "#F0FDFA"        # Very light teal tint for hover states
ACCENT = "#10B981"               # Emerald green — highlights, badges
ACCENT_LIGHT = "#ECFDF5"         # Light green tint

# Backgrounds — warm cream tones, not cold white
BG_PAGE = "#FAF9F7"              # Warm off-white page background
BG_SECTION = "#F5F3EF"           # Slightly warmer — sidebar, sections
BG_WARM = "#FFF8F0"              # Warm cream tint for hero/feature areas
SURFACE = "#FFFFFF"              # Card / panel backgrounds (true white)

# Text
TEXT_PRIMARY = "#1C1917"         # Stone-900 — headings, body text
TEXT_SECONDARY = "#57534E"       # Stone-600 — captions, muted text
TEXT_TERTIARY = "#A8A29E"        # Stone-400 — placeholders, disabled

# Borders & shadows — warm tones
BORDER = "#E7E5E4"              # Stone-200 — card borders, dividers
BORDER_LIGHT = "#F5F5F4"        # Stone-100 — subtle separators
SHADOW_SM = "0 1px 3px rgba(28,25,23,0.05), 0 1px 2px rgba(28,25,23,0.03)"
SHADOW_MD = "0 4px 16px rgba(28,25,23,0.06), 0 2px 4px rgba(28,25,23,0.03)"
SHADOW_LG = "0 8px 30px rgba(28,25,23,0.08), 0 4px 8px rgba(28,25,23,0.04)"

# Semantics
SUCCESS = "#059669"              # Green
ERROR = "#DC2626"                # Red
WARNING = "#D97706"              # Amber

# Radii — generous rounding for warmth
RADIUS = "12px"                  # Cards, panels
RADIUS_SM = "8px"                # Buttons, inputs
RADIUS_XL = "16px"               # Large containers

# Typography
FONT_STACK = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"


def inject_custom_css(theme: str = "light") -> None:
    """Inject the full custom CSS stylesheet into the Streamlit app."""
    st.markdown(_FONT_LINK + _CSS, unsafe_allow_html=True)
    if theme == "dark":
        st.markdown(_DARK_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Google Fonts — loaded via <link> tag (reliable across all browsers)
# ---------------------------------------------------------------------------
_FONT_LINK = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet">
"""

# ---------------------------------------------------------------------------
# Master stylesheet
# ---------------------------------------------------------------------------
_CSS = f"""
<style>
/* ====================================================================
   InsightPilot — Custom Theme (Joyful Innovation design system)
   Warm · Airy · Human
   ==================================================================== */

/* --- Root / body --------------------------------------------------- */
html, body, [data-testid="stApp"] {{
    font-family: {FONT_STACK} !important;
    background-color: {BG_PAGE} !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}}

/* --- Main content area --------------------------------------------- */
[data-testid="stMainBlockContainer"] {{
    max-width: 1100px;
}}

/* --- Headings ------------------------------------------------------ */
h1, h2, h3, h4, h5, h6,
[data-testid="stHeadingWithActionElements"] {{
    font-family: {FONT_STACK} !important;
    color: {TEXT_PRIMARY} !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
}}

h1 {{ font-size: 1.75rem !important; }}
h2 {{ font-size: 1.35rem !important; }}
h3 {{ font-size: 1.1rem !important; }}

/* --- Body text ----------------------------------------------------- */
/* NOTE: Do NOT override font-family on <span> globally — it breaks
   Material Symbols icon rendering (the icon font uses <span> elements). */
p, li, label, div:not([data-testid]) {{
    font-family: {FONT_STACK} !important;
}}

/* --- Sidebar — strong visual separation from content --------------- */
section[data-testid="stSidebar"] {{
    background-color: {BG_SECTION} !important;
    border-right: 1px solid {BORDER} !important;
    box-shadow: 2px 0 16px rgba(28,25,23,0.06), 1px 0 4px rgba(28,25,23,0.03) !important;
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
    transition: all 0.2s ease !important;
}}

button[data-testid="stBaseButton-primary"]:hover,
button[kind="primary"]:hover {{
    background-color: {PRIMARY_HOVER} !important;
    box-shadow: {SHADOW_SM} !important;
    transform: translateY(-1px);
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
    transition: all 0.2s ease !important;
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
    background-color: {SURFACE} !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
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
    padding: 1rem 1.25rem !important;
    box-shadow: {SHADOW_SM} !important;
}}

[data-testid="stMetricLabel"] {{
    color: {TEXT_SECONDARY} !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
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
    background-color: {SURFACE} !important;
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
    transition: color 0.2s ease !important;
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
    transition: background-color 0.2s ease !important;
    font-size: 0.875rem !important;
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
    background-color: {SURFACE} !important;
}}

/* --- Toast / success messages -------------------------------------- */
[data-testid="stToast"] {{
    border-radius: {RADIUS_SM} !important;
}}

/* --- Hide Streamlit branding --------------------------------------- */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
[data-testid="stHeader"] {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}}
[data-testid="stDecoration"] {{
    display: none !important;
}}

/* --- Sidebar content ordering -------------------------------------- */
section[data-testid="stSidebar"] > div:first-child {{
    display: flex;
    flex-direction: column;
}}

/* --- Sidebar navigation links -------------------------------------- */
[data-testid="stSidebarNav"] li a {{
    display: flex !important;
    align-items: center !important;
    gap: 0.5rem !important;
    padding: 0.45rem 0.75rem !important;
    font-size: 0.875rem !important;
}}

[data-testid="stSidebarNav"] li a span[data-testid="stIconMaterial"] {{
    font-size: 1.15rem !important;
    line-height: 1 !important;
}}

/* --- Sidebar nav group headers ------------------------------------- */
[data-testid="stSidebarNav"] h2 {{
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: {TEXT_TERTIARY} !important;
    font-weight: 600 !important;
    padding: 0.5rem 0.75rem 0.25rem !important;
    margin: 0 !important;
}}

/* ====================================================================
   Reusable utility classes (used by pages via st.markdown)
   ==================================================================== */

/* --- Card containers ----------------------------------------------- */
.ip-card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: {RADIUS};
    padding: 1.25rem 1.5rem;
    box-shadow: {SHADOW_SM};
    margin-bottom: 1rem;
    font-family: {FONT_STACK};
}}
.ip-card-hover {{
    transition: all 0.2s ease;
    cursor: pointer;
}}
.ip-card-hover:hover {{
    box-shadow: {SHADOW_MD};
    border-color: {PRIMARY};
    transform: translateY(-2px);
}}

/* --- Section headers ----------------------------------------------- */
.ip-section-header {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid {BORDER_LIGHT};
    font-family: {FONT_STACK};
}}
.ip-section-header h3 {{
    margin: 0 !important;
    font-size: 1.1rem !important;
}}

/* --- Status badges ------------------------------------------------- */
.ip-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    font-family: {FONT_STACK};
    letter-spacing: 0.02em;
}}
.ip-badge-success {{ background: #ECFDF5; color: #059669; }}
.ip-badge-error   {{ background: #FEF2F2; color: #DC2626; }}
.ip-badge-pending {{ background: #FFF7ED; color: #D97706; }}
.ip-badge-info    {{ background: #F0FDFA; color: #0F766E; }}
.ip-badge-trial   {{ background: linear-gradient(135deg, #F0FDFA, #ECFDF5); color: #0F766E; border: 1px solid #CCFBF1; }}

/* --- Stat number + label combo ------------------------------------- */
.ip-stat {{
    text-align: center;
    padding: 0.5rem;
}}
.ip-stat-value {{
    font-size: 1.5rem;
    font-weight: 700;
    color: {TEXT_PRIMARY};
    line-height: 1.2;
    font-family: {FONT_STACK};
}}
.ip-stat-label {{
    font-size: 0.7rem;
    color: {TEXT_SECONDARY};
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 500;
    font-family: {FONT_STACK};
}}

/* --- Empty state --------------------------------------------------- */
.ip-empty-state {{
    text-align: center;
    padding: 3rem 2rem;
    color: {TEXT_TERTIARY};
    font-family: {FONT_STACK};
}}

/* --- Action cards (for landing pages) ------------------------------ */
.ip-action-card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: {RADIUS};
    padding: 1.25rem;
    text-align: center;
    transition: all 0.2s ease;
    cursor: pointer;
    font-family: {FONT_STACK};
}}
.ip-action-card:hover {{
    border-color: {PRIMARY};
    box-shadow: {SHADOW_MD};
    transform: translateY(-2px);
}}
.ip-action-card .icon {{
    font-size: 2rem;
    margin-bottom: 0.5rem;
    color: {PRIMARY};
}}
.ip-action-card .title {{
    font-weight: 600;
    color: {TEXT_PRIMARY};
    font-size: 0.95rem;
    margin-bottom: 0.25rem;
}}
.ip-action-card .desc {{
    font-size: 0.8rem;
    color: {TEXT_SECONDARY};
}}

/* --- Trial banner -------------------------------------------------- */
.ip-trial-banner {{
    background: linear-gradient(135deg, #F0FDFA 0%, #ECFDF5 100%);
    border: 1px solid #CCFBF1;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 12px;
    font-family: {FONT_STACK};
}}
.ip-trial-banner .label {{
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: {PRIMARY};
    margin-bottom: 2px;
}}
.ip-trial-banner .days {{
    font-size: 0.85rem;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}

</style>
"""

# ---------------------------------------------------------------------------
# Dark mode override stylesheet
# ---------------------------------------------------------------------------
_DARK_CSS = f"""
<style>
/* ====================================================================
   InsightPilot — Dark Mode Overrides
   ==================================================================== */

html, body, [data-testid="stApp"] {{
    background-color: #1A1A1E !important;
    color: #F5F5F4 !important;
}}

section[data-testid="stSidebar"] {{
    background-color: #1F1F23 !important;
    border-right-color: #2A2A2E !important;
    box-shadow: 2px 0 16px rgba(0,0,0,0.3), 1px 0 4px rgba(0,0,0,0.2) !important;
}}

section[data-testid="stSidebar"] .stMarkdown {{
    color: #F5F5F4 !important;
}}

h1, h2, h3, h4, h5, h6,
[data-testid="stHeadingWithActionElements"] {{
    color: #F5F5F4 !important;
}}

p, li, label, div:not([data-testid]) {{
    color: #D6D3D1 !important;
}}

/* Inputs */
input[type="text"], input[type="password"], input[type="email"],
input[type="number"], textarea,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {{
    background-color: #2A2A2E !important;
    border-color: #3A3A3E !important;
    color: #F5F5F4 !important;
}}

/* Metrics */
[data-testid="stMetric"] {{
    background-color: #2A2A2E !important;
    border-color: #3A3A3E !important;
}}

[data-testid="stMetricValue"] {{
    color: #F5F5F4 !important;
}}

[data-testid="stMetricLabel"] {{
    color: #A8A29E !important;
}}

/* Buttons — secondary */
button[data-testid="stBaseButton-secondary"],
button[kind="secondary"] {{
    background-color: #2A2A2E !important;
    color: #F5F5F4 !important;
    border-color: #3A3A3E !important;
}}

/* Expanders */
[data-testid="stExpander"] {{
    background-color: #2A2A2E !important;
    border-color: #3A3A3E !important;
}}

/* Forms */
[data-testid="stForm"] {{
    background-color: #2A2A2E !important;
    border-color: #3A3A3E !important;
}}

/* Selectboxes */
[data-testid="stSelectbox"] > div > div {{
    border-color: #3A3A3E !important;
}}

/* Tabs */
button[data-baseweb="tab"] {{
    color: #A8A29E !important;
}}

/* Dividers */
hr {{
    border-color: #3A3A3E !important;
}}

/* Cards / utility classes */
.ip-card {{
    background: #2A2A2E;
    border-color: #3A3A3E;
}}
.ip-card-hover:hover {{
    border-color: {PRIMARY};
}}

.ip-stat-value {{
    color: #F5F5F4;
}}
.ip-stat-label {{
    color: #A8A29E;
}}

.ip-action-card {{
    background: #2A2A2E;
    border-color: #3A3A3E;
}}
.ip-action-card:hover {{
    border-color: {PRIMARY};
}}
.ip-action-card .title {{
    color: #F5F5F4;
}}
.ip-action-card .desc {{
    color: #A8A29E;
}}

.ip-trial-banner {{
    background: linear-gradient(135deg, #1A2A28 0%, #1F2A25 100%);
    border-color: #2A3A38;
}}
.ip-trial-banner .days {{
    color: #F5F5F4;
}}

/* Data tables */
[data-testid="stDataFrame"] {{
    border-color: #3A3A3E !important;
}}

/* Captions */
[data-testid="stCaptionContainer"] {{
    color: #A8A29E !important;
}}

</style>
"""
