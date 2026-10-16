from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from apps.api.app.db import get_db
from apps.api.app.models.entities import Company, Job, JobSourceOccurrence
from apps.api.app.schemas.jobs import JobList, JobOut
from apps.api.app.services.jobs import serialize_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def pattern(value: str) -> str:
    return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


@router.get("", response_model=JobList)
def list_jobs(
    keyword: str = Query("", max_length=200),
    location: str = Query("", max_length=200),
    remote: bool | None = None,
    employment_type: str = Query("", max_length=80),
    experience_level: str = Query("", max_length=80),
    company: str = Query("", max_length=250),
    source: str = Query("", max_length=80),
    posted_after: datetime | None = None,
    limit: int = Query(12, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
    db: Session = Depends(get_db),
) -> JobList:
    statement = select(Job).join(Company).where(Job.active.is_(True))
    if keyword:
        statement = statement.where(
            or_(
                Job.title.ilike(pattern(keyword), escape="\\"),
                Job.description.ilike(pattern(keyword), escape="\\"),
            )
        )
    for value, column in [
        (location, Job.location),
        (employment_type, Job.employment_type),
        (experience_level, Job.experience_level),
        (company, Company.name),
    ]:
        if value:
            statement = statement.where(column.ilike(pattern(value), escape="\\"))
    if remote is not None:
        statement = statement.where(Job.remote == remote)
    if source:
        statement = statement.where(Job.occurrences.any(JobSourceOccurrence.source_name == source))
    if posted_after:
        statement = statement.where(Job.posted_at >= posted_after)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    jobs = db.scalars(
        statement.order_by(Job.posted_at.desc().nullslast(), Job.id).offset(offset).limit(limit)
    )
    return JobList(
        items=[serialize_job(job) for job in jobs], total=total, limit=limit, offset=offset
    )


# Keep this dynamic route after /recommended when the recommendations router is mounted.
@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobOut:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return serialize_job(job)
