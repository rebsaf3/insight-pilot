"""FastAPI server — REST API, Stripe webhooks, SSO callbacks.
Run with: uvicorn api.server:app --port 8100
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from config.settings import API_SERVER_PORT
from db.database import init_db

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


# Mount route modules
from api.routes import projects, files, dashboards, analysis, account, webhooks
from auth.sso import router as sso_router

app.include_router(projects.router, prefix="/api/v1", tags=["Projects"])
app.include_router(files.router, prefix="/api/v1", tags=["Files"])
app.include_router(dashboards.router, prefix="/api/v1", tags=["Dashboards"])
app.include_router(analysis.router, prefix="/api/v1", tags=["Analysis"])
app.include_router(account.router, prefix="/api/v1", tags=["Account"])
app.include_router(webhooks.router, tags=["Webhooks"])
app.include_router(sso_router, tags=["SSO"])


@app.get("/health")
def health():
    return {"status": "ok"}
