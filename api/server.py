"""FastAPI server — REST API, Stripe webhooks, SSO callbacks.
Run with: uvicorn api.server:app --port 8100
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import API_SERVER_PORT
from db.database import init_db
from api.rate_limiter import api_rate_limiter

app = FastAPI(
    title="InsightPilot API",
    version="1.0.0",
    description="REST API for InsightPilot data analytics platform",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limit API requests by API key or IP."""
    # Skip rate limiting for non-API routes
    if not request.url.path.startswith("/api/v1"):
        return await call_next(request)

    # Use API key prefix or IP as the rate limit key
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        key = auth_header[7:12]  # Use first 5 chars of key
    else:
        key = request.client.host if request.client else "unknown"

    if not api_rate_limiter.allow(key):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Max 100 requests per minute."},
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(api_rate_limiter.remaining(key))
    return response


# Mount route modules
from api.routes import projects, files, dashboards, analysis, account, webhooks, scim, gdpr
from auth.sso import router as sso_router

app.include_router(projects.router, prefix="/api/v1", tags=["Projects"])
app.include_router(files.router, prefix="/api/v1", tags=["Files"])
app.include_router(dashboards.router, prefix="/api/v1", tags=["Dashboards"])
app.include_router(analysis.router, prefix="/api/v1", tags=["Analysis"])
app.include_router(account.router, prefix="/api/v1", tags=["Account"])
app.include_router(webhooks.router, tags=["Webhooks"])
app.include_router(sso_router, tags=["SSO"])
app.include_router(scim.router, prefix="/api/v1", tags=["SCIM"])
app.include_router(gdpr.router, prefix="/api/v1", tags=["GDPR"])


@app.get("/health")
def health():
    return {"status": "ok"}
