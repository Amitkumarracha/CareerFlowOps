from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.config import get_settings
from apps.api.app.db import get_db
from apps.api.app.dependencies.auth import admin
from apps.api.app.models.entities import IngestionRun
from apps.api.app.schemas.admin import IngestionRequest, IngestionResponse
from ingestion.runner import run_ingestion

router = APIRouter(prefix="/api/admin", dependencies=[Depends(admin)], tags=["admin"])


@router.post("/ingestion/run", response_model=IngestionResponse)
def ingest(request: IngestionRequest, db: Session = Depends(get_db)) -> IngestionRun:
    try:
        return run_ingestion(db, get_settings().data_dir, request.mode == "fixture")
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/ingestion/status", response_model=list[IngestionResponse])
def status(db: Session = Depends(get_db)) -> list[IngestionRun]:
    return list(db.scalars(select(IngestionRun).order_by(IngestionRun.created_at.desc()).limit(20)))
