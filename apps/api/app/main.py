from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from apps.api.app.config import get_settings
from apps.api.app.db import get_db
from apps.api.app.observability import instrument
from apps.api.app.routes.admin import router as admin_router
from apps.api.app.routes.analytics import router as analytics_router
from apps.api.app.routes.applications import router as application_router
from apps.api.app.routes.jobs import router as jobs_router
from apps.api.app.routes.profile import router as profile_router
from apps.api.app.routes.recommendations import router as recommendation_router
from apps.api.app.schemas.health import Health
from ml.inference.bundle import load_bundle

settings = get_settings()
app = FastAPI(title="CareerFlowOps", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok")


@app.get("/ready", response_model=Health)
def ready(db: Session = Depends(get_db)) -> Health:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Database unavailable") from exc
    if settings.model_bundle_path is not None:
        try:
            bundle = load_bundle(str(settings.model_bundle_path))
        except RuntimeError as exc:
            raise HTTPException(503, "Production model unavailable") from exc
        return Health(
            status="ready",
            model_version=bundle.config["model_version"],
            algorithm=bundle.config["algorithm"],
            bundle_id=bundle.bundle_id,
        )
    return Health(status="ready")


app.include_router(admin_router)

app.include_router(recommendation_router)
app.include_router(jobs_router)

app.include_router(profile_router)

app.include_router(application_router)

app.include_router(analytics_router)

instrument(app)
