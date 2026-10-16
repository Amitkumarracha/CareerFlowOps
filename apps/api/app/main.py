from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from apps.api.app.config import get_settings
from apps.api.app.db import get_db
from apps.api.app.schemas.health import Health

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
    return Health(status="ready")
