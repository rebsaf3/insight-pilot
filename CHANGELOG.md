# Changelog

All notable changes to InsightPilot are documented in this file.

## [1.0.0] - 2026-02-13

### Initial Release

Full SaaS platform for AI-powered data analytics with subscription tiers, multi-tenant workspaces, and a REST API.

---

### Added

#### Core Platform
- Streamlit-based web application with wide layout and page navigation
- SQLite database with WAL mode, foreign keys, and 17 tables
- Central configuration system with environment variable loading

#### Authentication & Security
- Email/password registration and login with bcrypt hashing
- Token-based session management with configurable expiry (30 days)
- Two-factor authentication: TOTP (Google Authenticator), email verification codes, backup codes
- TOTP secrets encrypted at rest using Fernet symmetric encryption
- Role-based access control with 4 roles: Owner, Admin, Member, Viewer
- Permission enforcement at both UI and query layers

#### SSO (Single Sign-On)
- Google OpenID Connect integration (Pro+ tiers)
- Microsoft Azure AD / Entra ID via OIDC (Pro+ tiers)
- SAML 2.0 support for enterprise IdPs — Okta, OneLogin, PingFederate (Enterprise tier)
- CSRF protection via signed state tokens (JWT)
- Automatic user creation on first SSO login
- Workspace-level SSO configuration with optional password login disable
- SP metadata endpoint for SAML configuration

#### Workspace System
- Personal and shared workspaces with automatic creation on registration
- Member management: invite, change roles, remove
- Invitation system with token-based acceptance and expiry
- Multi-tenancy enforcement: all database queries scoped by workspace_id

#### Data Pipeline
- File upload supporting CSV, Excel (.xlsx/.xls), and JSON formats
- Automatic encoding detection for CSV files (chardet with fallback chain)
- JSON normalization for nested structures
- Data profiler: column type inference (numeric, categorical, datetime, boolean, text), statistics, null analysis, sample values
- Tier-gated upload limits (files/day, file size)

#### AI Analysis
- Claude API integration (claude-sonnet-4-5-20250929) with temperature 0.0
- 3-step analysis wizard: Describe, Review, Save
- Structured prompt engineering with data profile context and few-shot examples
- Auto-retry on code generation failure (up to 2 retries with error context)
- Safe code execution with 5 security layers:
  - AST validation (import whitelist, dangerous call detection)
  - Restricted `__import__` allowing only whitelisted modules
  - Filtered builtins (no `open`, `exec`, `eval`, `compile`)
  - Threaded execution with 30-second timeout
  - Read-only data (df.copy())

#### Credit System
- Token-based pricing: 1 credit per 1,000 tokens (input + output)
- 3 subscription tiers: Free (50 credits), Pro (500 credits), Enterprise (2,000 credits)
- Real-time balance tracking with ledger-based accounting
- Tier-specific limits: uploads/day, file size, dashboards, revisions, export
- Credit top-ups via Stripe ($10 per 100 credits, Pro+ only)

#### Billing & Payments
- Stripe integration for subscription management
- Checkout sessions for plan upgrades, credit top-ups, and API add-on
- Webhook handling: checkout completion, invoice payment, subscription updates/cancellation
- Billing page with plan comparison, upgrade/downgrade, credit history
- API Access add-on ($15/mo) for Pro and Enterprise plans

#### Dashboards & Export
- Dashboard persistence with grid layout rendering
- Chart reordering, deletion, and renaming
- PDF export: title page + landscape chart pages with prompt text (Pro+ only)
- PNG export for individual charts (Pro+ only)

#### Report Branding
- Workspace-level branding: logo upload, primary/secondary/accent colors, font family, chart color palettes
- Dashboard-level style overrides (layout columns, background, title styling)
- Chart-level style overrides (titles, axis labels, legend, per-series colors)
- 8 built-in chart color palettes + custom palette support
- 10 available font families
- Branding applied post-generation via `apply_branding()` on Plotly figures
- Enterprise white-label: removable InsightPilot branding
- Live preview in the branding editor
- Tier gates: Free (default only), Pro (custom), Enterprise (full white-label)

#### REST API
- FastAPI server with CORS and health check endpoint
- API key authentication with SHA-256 hashing (key shown once, prefix stored)
- Scoped permissions per key: read, write, analyze
- Token bucket rate limiting: 100 requests/minute per key with `X-RateLimit-Remaining` headers
- Full CRUD endpoints: projects, files, dashboards
- AI analysis endpoint with code generation, execution, auto-retry, and credit deduction
- Account/usage info endpoints
- Stripe webhook endpoint
- Pydantic request/response schemas

#### UI Pages
- **Login** — Sign in / register with 2FA verification (TOTP, email, backup codes) and SSO buttons
- **Projects** — List, create, navigate to upload/analyze
- **Upload** — File upload with validation, preview, and automatic profiling
- **Analyze** — 3-step wizard with credit estimation, revision support, and dashboard save
- **Dashboard View** — Grid rendering with Plotly charts and export button
- **Dashboard Edit** — Reorder, delete charts, rename/delete dashboard
- **Billing** — Plan comparison table, upgrade buttons, credit top-ups, add-on management, credit history
- **Branding** — Color pickers, font selector, palette chooser, logo upload, live preview with tier gates
- **Workspace Settings** — General settings, member management (roles, invite, remove), SSO configuration (Google, Microsoft, SAML)
- **Account Settings** — Profile edit, password change, 2FA setup/manage (TOTP QR code, email toggle, backup codes), session management with revoke
- **API Settings** — Create/revoke API keys with permission scoping, quick start documentation

#### Sidebar
- Global workspace selector dropdown
- Credit balance and tier display
- Active project indicator
- Upgrade prompt for free tier users

#### Testing
- 81 tests across 5 test modules (all passing)
- Code executor security tests: AST validation, import blocking, builtin restrictions
- Authentication tests: registration, login, SSO handling, password hashing
- Multi-tenancy tests: workspace isolation, project scoping
- Role and permission tests: owner/admin/member/viewer access levels
- Credit system tests: balance tracking, deductions, cost calculation, tier limits
- API key tests: generation, verification, revocation, permission scoping
- Rate limiter tests: token bucket, key independence
- Data profiler tests: column type inference, statistics, null handling, edge cases
