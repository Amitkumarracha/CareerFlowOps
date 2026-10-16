import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.app.models.entities import Company, Job, JobSource, JobSourceOccurrence


def test_multiple_sources_preserve_provenance(db: Session) -> None:
    company = Company(name="Test company")
    db.add(company)
    db.flush()
    job = Job(company_id=company.id, title="Engineer", fingerprint="test")
    db.add(job)
    db.flush()
    for source_name in ["greenhouse", "lever"]:
        source = JobSource(name=source_name, board="test")
        db.add(source)
        db.flush()
        db.add(
            JobSourceOccurrence(
                job_id=job.id,
                source_id=source.id,
                source_name=source_name,
                source_job_id="1",
                source_url="https://example.org/job",
                apply_url="https://example.org/apply",
                source_payload_hash="abc",
                raw_path="raw/abc.json",
            )
        )
    db.commit()
    db.expire_all()
    assert len(db.scalars(select(Job)).one().occurrences) == 2


def test_company_uniqueness(db: Session) -> None:
    db.add_all([Company(name="duplicate"), Company(name="duplicate")])
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
