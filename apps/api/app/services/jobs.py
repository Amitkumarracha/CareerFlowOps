from apps.api.app.models.entities import Job
from apps.api.app.schemas.jobs import JobOut, OccurrenceOut


def serialize_job(job: Job) -> JobOut:
    sources = sorted(
        job.occurrences,
        key=lambda occurrence: (
            occurrence.verification_status == "official_api",
            occurrence.last_seen_at,
            occurrence.id,
        ),
        reverse=True,
    )
    return JobOut(
        id=job.id,
        title=job.title,
        company=job.company.name,
        location=job.location,
        description=job.description,
        employment_type=job.employment_type,
        experience_level=job.experience_level,
        remote=job.remote,
        posted_at=job.posted_at,
        first_seen_at=job.created_at,
        last_seen_at=job.last_seen_at,
        skills=[skill.skill for skill in job.skills],
        apply_url=sources[0].apply_url if sources else None,
        sources=[OccurrenceOut.model_validate(occurrence) for occurrence in sources],
    )
