from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.app.db import get_db
from apps.api.app.dependencies.auth import candidate
from apps.api.app.models.entities import Application, ApplicationHistory, Job, SavedJob, now
from apps.api.app.schemas.applications import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationUpdate,
    SavedOut,
    SaveRequest,
)
from apps.api.app.services.jobs import serialize_job

router = APIRouter(prefix="/api", tags=["applications"])


def application_out(application: Application) -> dict:
    return {
        "id": application.id,
        "job": serialize_job(application.job),
        "status": application.status,
        "notes": application.notes,
        "updated_at": application.updated_at,
        "history": application.history,
    }


def ensure_application(db: Session, candidate_id: str, data: ApplicationCreate) -> Application:
    existing = db.scalar(
        select(Application).where(
            Application.candidate_id == candidate_id, Application.job_id == data.job_id
        )
    )
    if existing:
        return existing
    try:
        with db.begin_nested():
            application = Application(
                candidate_id=candidate_id, job_id=data.job_id, status=data.status, notes=data.notes
            )
            db.add(application)
            db.flush()
            application.history.append(ApplicationHistory(status=data.status, notes=data.notes))
            db.flush()
    except IntegrityError:
        application = db.scalars(
            select(Application).where(
                Application.candidate_id == candidate_id, Application.job_id == data.job_id
            )
        ).one()
    return application


@router.get("/saved", response_model=list[SavedOut])
def saved(candidate_id: str = Depends(candidate), db: Session = Depends(get_db)) -> list[dict]:
    pairs = db.execute(
        select(SavedJob, Job)
        .join(Job, SavedJob.job_id == Job.id)
        .where(SavedJob.candidate_id == candidate_id)
        .order_by(SavedJob.created_at.desc())
        .limit(1000)
    ).all()
    return [
        {"id": record.id, "job": serialize_job(job), "created_at": record.created_at}
        for record, job in pairs
    ]


@router.post("/saved", response_model=SavedOut)
def save_job(
    data: SaveRequest, candidate_id: str = Depends(candidate), db: Session = Depends(get_db)
) -> dict:
    job = db.get(Job, data.job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    record = db.scalar(
        select(SavedJob).where(SavedJob.candidate_id == candidate_id, SavedJob.job_id == job.id)
    )
    if record is None:
        try:
            with db.begin_nested():
                record = SavedJob(candidate_id=candidate_id, job_id=job.id)
                db.add(record)
                db.flush()
        except IntegrityError:
            record = db.scalars(
                select(SavedJob).where(
                    SavedJob.candidate_id == candidate_id, SavedJob.job_id == job.id
                )
            ).one()
    ensure_application(db, candidate_id, ApplicationCreate(job_id=job.id))
    db.commit()
    return {"id": record.id, "job": serialize_job(job), "created_at": record.created_at}


@router.delete("/saved/{job_id}", status_code=204)
def unsave(
    job_id: str, candidate_id: str = Depends(candidate), db: Session = Depends(get_db)
) -> Response:
    record = db.scalar(
        select(SavedJob).where(SavedJob.candidate_id == candidate_id, SavedJob.job_id == job_id)
    )
    if record:
        db.delete(record)
        db.commit()
    return Response(status_code=204)


@router.get("/applications", response_model=list[ApplicationOut])
def applications(
    candidate_id: str = Depends(candidate), db: Session = Depends(get_db)
) -> list[dict]:
    rows = db.scalars(
        select(Application)
        .where(Application.candidate_id == candidate_id)
        .order_by(Application.updated_at.desc())
        .limit(1000)
    )
    return [application_out(row) for row in rows]


@router.post("/applications", response_model=ApplicationOut)
def create_application(
    data: ApplicationCreate, candidate_id: str = Depends(candidate), db: Session = Depends(get_db)
) -> dict:
    if db.get(Job, data.job_id) is None:
        raise HTTPException(404, "Job not found")
    application = ensure_application(db, candidate_id, data)
    db.commit()
    return application_out(application)


@router.patch("/applications/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: str,
    data: ApplicationUpdate,
    candidate_id: str = Depends(candidate),
    db: Session = Depends(get_db),
) -> dict:
    application = db.scalar(
        select(Application)
        .where(Application.id == application_id, Application.candidate_id == candidate_id)
        .with_for_update(of=Application)
    )
    if application is None:
        raise HTTPException(404, "Application not found")
    if application.status != data.status or application.notes != data.notes:
        application.status = data.status
        application.notes = data.notes
        application.updated_at = now()
        application.history.append(ApplicationHistory(status=data.status, notes=data.notes))
        db.commit()
    return application_out(application)
