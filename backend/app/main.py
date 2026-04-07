from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.init_db import init_db
from app.api.routes.health import router as health_router
from app.api.routes.resume import router as resume_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.match import router as match_router
from app.api.routes.applications import router as applications_router
from app.api.routes.autopilot import router as autopilot_router

app = FastAPI(title="Job Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(resume_router)
app.include_router(jobs_router)
app.include_router(match_router)
app.include_router(applications_router)
app.include_router(autopilot_router)


@app.on_event("startup")
def ensure_local_schema() -> None:
    if settings.database_url.startswith("sqlite"):
        init_db()


@app.get("/")
def root():
    return {"status": "ok"}
