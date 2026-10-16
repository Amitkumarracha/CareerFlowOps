from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.config import get_settings
from apps.api.app.db import get_db
from apps.api.app.dependencies.auth import admin
from apps.api.app.models.entities import IngestionRun, Job
from apps.api.app.schemas.admin import DedupResponse, IngestionRequest, IngestionResponse
from ingestion.dedup import possible_duplicates
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


@router.get("/dedup", response_model=DedupResponse)
def dedup(db: Session = Depends(get_db)) -> dict:
    jobs = list(db.scalars(select(Job).order_by(Job.last_seen_at.desc(), Job.id).limit(200)))
    return {
        "jobs": [
            {
                "id": job.id,
                "title": job.title,
                "fingerprint": job.fingerprint,
                "source_occurrences": len(job.occurrences),
                "sources": sorted({o.source_name for o in job.occurrences}),
            }
            for job in jobs
        ],
        "possible_duplicates": possible_duplicates(jobs),
    }
