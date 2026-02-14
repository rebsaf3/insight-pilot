# InsightPilot

AI-powered data analytics platform. Upload your data, describe the report you want, and let Claude generate interactive dashboards and visualizations.

## Features

### Core Analytics
- **Data Upload** — CSV, Excel (.xlsx/.xls), and JSON file support with automatic profiling
- **AI-Powered Analysis** — 3-step wizard: describe your report, review the generated chart, save to a dashboard
- **Interactive Dashboards** — Grid layout with Plotly charts, reordering, editing, and export (PDF/PNG)
- **Auto-Retry** — Failed chart generation automatically retries with error context (up to 2 retries)

### Credit System
- Token-based pricing: 1 credit per 1,000 tokens (input + output)
- Monthly allowances by tier, plus on-demand top-ups via Stripe
- Real-time balance tracking in the sidebar

### Subscription Tiers

| Feature | Free | Pro ($29/mo) | Enterprise ($99/mo) |
|---|---|---|---|
| Monthly credits | 50 | 500 | 2,000 |
| Uploads/day | 1 | 10 | Unlimited |
| Max file size | 10 MB | 100 MB | 500 MB |
| Revisions | None | Unlimited | Unlimited |
| Dashboards | 3 | 25 | Unlimited |
| Export (PDF/PNG) | No | Yes | Yes |
| Credit top-ups | No | $10/100 credits | $10/100 credits |
| Members | 1 | 10 | Unlimited |
| Branding | Default | Custom colors/fonts/logo | Full white-label |
| SSO | No | Google + Microsoft | Google + Microsoft + SAML |
| API access | No | Add-on ($15/mo) | Add-on ($15/mo) |

### Authentication & Security
- Email/password registration with bcrypt hashing
- **Two-Factor Authentication** — TOTP (Google Authenticator), email codes, backup codes
- TOTP secrets encrypted at rest with Fernet
- Session management with token-based auth and expiry
- Role-based access control: Owner, Admin, Member, Viewer

### SSO (Single Sign-On)
- **Google** — OpenID Connect (Pro+)
- **Microsoft** — Azure AD / Entra ID via OIDC (Pro+)
- **SAML 2.0** — Okta, OneLogin, PingFederate, Azure AD SAML (Enterprise)
- Workspace-level SSO configuration with optional password login disable

### Report Branding
- Workspace-level: logo, colors, fonts, chart color palettes
- Dashboard-level: layout columns, background, title styling
- Chart-level: titles, axis labels, legend, per-series colors
- Branding applied post-generation (keeps LLM prompts clean)
- Enterprise white-label: remove InsightPilot branding

### REST API
- Full CRUD for projects, files, dashboards
- AI analysis endpoint with credit deduction
- API key authentication with scoped permissions (read/write/analyze)
- Rate limiting: 100 requests/minute per key
- Available as an add-on ($15/mo) on Pro and Enterprise plans

### Workspace System
- Personal and shared workspaces (Notion-style)
- Role-based access: Owner, Admin, Member, Viewer
- Member invitations with token-based acceptance
- Multi-tenancy: all data queries scoped by workspace_id

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | Streamlit |
| LLM | Anthropic Claude (claude-sonnet-4-5-20250929) |
| Database | SQLite (WAL mode, 17 tables) |
| API Server | FastAPI + Uvicorn |
| Payments | Stripe (subscriptions, webhooks, top-ups) |
| Charts | Plotly |
| Export | kaleido (images) + fpdf2 (PDF) |
| Auth | bcrypt, PyJWT, pyotp, cryptography |
| SSO | httpx + PyJWT (OIDC), XML parsing (SAML) |

## Project Structure

```
app.py                          # Streamlit entrypoint
config/settings.py              # Central configuration, tier definitions
db/
  database.py                   # SQLite connection, 17-table schema
  models.py                     # Dataclass models
  queries.py                    # All CRUD operations (multi-tenant)
auth/
  authenticator.py              # Registration, login, password hashing
  session.py                    # Session management, permissions
  sso.py                        # SSO callback handlers (FastAPI)
services/
  llm_service.py                # Claude API integration
  code_executor.py              # Safe code execution (AST + sandbox)
  file_service.py               # File upload, parsing (CSV/Excel/JSON)
  data_profiler.py              # Column type inference, statistics
  credit_service.py             # Balance, deductions, tier limits
  stripe_service.py             # Subscriptions, webhooks, top-ups
  branding_service.py           # Workspace branding, apply to charts
  export_service.py             # PDF/PNG export
  workspace_service.py          # Workspace creation, invitations
  tfa_service.py                # TOTP, email codes, backup codes
  sso_service.py                # Google/Microsoft OIDC, SAML
  api_key_service.py            # API key generation, verification
prompts/
  system_prompt.py              # LLM system prompt
  few_shot_examples.py          # Example prompt/code pairs
  prompt_builder.py             # Message assembly
pages/
  login.py                      # Login/register with 2FA and SSO
  projects.py                   # Project list and creation
  upload.py                     # File upload with preview/profile
  analyze.py                    # 3-step analysis wizard
  dashboard_view.py             # Dashboard grid rendering
  dashboard_edit.py             # Reorder/delete charts
  billing.py                    # Plan management, top-ups, add-ons
  branding.py                   # Style editor with live preview
  workspace_settings.py         # Members, invitations, SSO config
  settings.py                   # Profile, password, 2FA, sessions
  api_settings.py               # API key management
api/
  server.py                     # FastAPI app with middleware
  auth.py                       # API key verification
  schemas.py                    # Pydantic request/response models
  rate_limiter.py               # Token bucket rate limiter
  routes/                       # REST endpoints
components/sidebar.py           # Workspace selector, credit display
tests/                          # 81 tests (pytest)
```

## Quick Start

### Prerequisites
- Python 3.12+
- An [Anthropic API key](https://console.anthropic.com/)

### Setup

```bash
# Clone the repository
git clone https://github.com/rebsaf3/insight-pilot.git
cd insight-pilot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (at minimum: ANTHROPIC_API_KEY, APP_SECRET_KEY)
```

### Run

```bash
# Start the Streamlit app
streamlit run app.py

# Start the API server (in a separate terminal)
uvicorn api.server:app --port 8100
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `APP_SECRET_KEY` | Yes | Random string for session signing |
| `ENCRYPTION_KEY` | Recommended | Fernet key for TOTP secret encryption |
| `STRIPE_SECRET_KEY` | For billing | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | For billing | Stripe webhook signing secret |
| `SMTP_USER` / `SMTP_PASSWORD` | For email 2FA | SMTP credentials |
| `GOOGLE_CLIENT_ID` / `SECRET` | For SSO | Google OAuth credentials |
| `MICROSOFT_CLIENT_ID` / `SECRET` | For SSO | Azure AD credentials |

See `.env.example` for the full list.

### Run Tests

```bash
pytest tests/ -v
```

## Code Execution Security

Generated Python code runs through 5 security layers:

1. **AST Validation** — Static analysis rejects non-whitelisted imports, dangerous function calls (`open`, `exec`, `eval`, `subprocess`), and blocked attribute access
2. **Restricted `__import__`** — Only whitelisted modules can be imported at runtime (pandas, numpy, plotly, datetime, math, statistics, json, re)
3. **Filtered Builtins** — `open`, `exec`, `eval`, `compile`, `__import__` (raw), `globals`, `locals` removed from builtins
4. **Timeout** — Threaded execution with configurable timeout (default 30s)
5. **Read-Only Data** — `df.copy()` passed to execution; original data never modified

## API Endpoints

All endpoints require `Authorization: Bearer ip_xxxxxxxxxxxx` header.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/projects` | List projects |
| `POST` | `/api/v1/projects` | Create project |
| `GET` | `/api/v1/projects/{id}` | Get project |
| `PUT` | `/api/v1/projects/{id}` | Update project |
| `DELETE` | `/api/v1/projects/{id}` | Delete project |
| `POST` | `/api/v1/projects/{id}/upload` | Upload file |
| `GET` | `/api/v1/projects/{id}/files` | List files |
| `DELETE` | `/api/v1/projects/{id}/files/{fid}` | Delete file |
| `GET` | `/api/v1/projects/{id}/dashboards` | List dashboards |
| `POST` | `/api/v1/projects/{id}/dashboards` | Create dashboard |
| `GET` | `/api/v1/dashboards/{id}` | Get dashboard + charts |
| `DELETE` | `/api/v1/dashboards/{id}` | Delete dashboard |
| `POST` | `/api/v1/analyze` | Run AI analysis |
| `GET` | `/api/v1/workspace` | Workspace info |
| `GET` | `/api/v1/workspace/usage` | Usage summary |

## License

All rights reserved.
