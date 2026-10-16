from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.app.db import Base


def uid() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(UTC)


class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Company(Identity, Base):
    __tablename__ = "companies"
    name: Mapped[str] = mapped_column(String(250), unique=True)


class Job(Identity, Base):
    __tablename__ = "jobs"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    title: Mapped[str] = mapped_column(String(500))
    location: Mapped[str] = mapped_column(String(500), default="Unknown")
    description: Mapped[str] = mapped_column(Text, default="")
    employment_type: Mapped[str | None] = mapped_column(String(80))
    experience_level: Mapped[str | None] = mapped_column(String(80))
    remote: Mapped[bool | None]
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    active: Mapped[bool] = mapped_column(default=True)
    company: Mapped[Company] = relationship(lazy="joined")
    occurrences: Mapped[list["JobSourceOccurrence"]] = relationship(lazy="selectin")
    skills: Mapped[list["JobSkill"]] = relationship(lazy="selectin", cascade="all, delete-orphan")


class JobSource(Identity, Base):
    __tablename__ = "job_sources"
    __table_args__ = (UniqueConstraint("name", "board"),)
    name: Mapped[str] = mapped_column(String(80))
    board: Mapped[str] = mapped_column(String(200))


class JobSourceOccurrence(Identity, Base):
    __tablename__ = "job_source_occurrences"
    __table_args__ = (UniqueConstraint("source_id", "source_job_id"),)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("job_sources.id"))
    source_name: Mapped[str] = mapped_column(String(80))
    source_job_id: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(Text)
    apply_url: Mapped[str] = mapped_column(Text)
    source_payload_hash: Mapped[str] = mapped_column(String(64))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    source_posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[str] = mapped_column(String(40), default="snapshot")
    raw_path: Mapped[str] = mapped_column(Text)


class Candidate(Identity, Base):
    __tablename__ = "candidates"
    active: Mapped[bool] = mapped_column(default=True)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(250))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(80))
    location: Mapped[str | None] = mapped_column(String(250))
    experience_years: Mapped[float | None]
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    education: Mapped[str] = mapped_column(Text, default="")
    experience: Mapped[str] = mapped_column(Text, default="")
    projects: Mapped[str] = mapped_column(Text, default="")
    certifications: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Resume(Identity, Base):
    __tablename__ = "resumes"
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    filename: Mapped[str] = mapped_column(String(250))
    extracted_text: Mapped[str] = mapped_column(Text)
    extracted_profile: Mapped[dict[str, Any]] = mapped_column(JSON)


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), primary_key=True)
    skill: Mapped[str] = mapped_column(String(100), primary_key=True)


class JobSkill(Base):
    __tablename__ = "job_skills"
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), primary_key=True)
    skill: Mapped[str] = mapped_column(String(100), primary_key=True)


class SavedJob(Identity, Base):
    __tablename__ = "saved_jobs"
    __table_args__ = (UniqueConstraint("candidate_id", "job_id"),)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))


class Application(Identity, Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("candidate_id", "job_id"),)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    status: Mapped[str] = mapped_column(String(30), default="SAVED")
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    job: Mapped[Job] = relationship(lazy="joined")
    history: Mapped[list["ApplicationHistory"]] = relationship(
        lazy="selectin", order_by="ApplicationHistory.changed_at", cascade="all, delete-orphan"
    )


class ApplicationHistory(Identity, Base):
    __tablename__ = "application_history"
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    status: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str] = mapped_column(Text, default="")
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ModelExperiment(Identity, Base):
    __tablename__ = "model_experiments"
    run_id: Mapped[str] = mapped_column(String(100), unique=True)
    algorithm: Mapped[str] = mapped_column(String(80))
    dataset_version: Mapped[str] = mapped_column(String(64))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON)
    artifact_path: Mapped[str] = mapped_column(Text)


class ModelDeployment(Identity, Base):
    __tablename__ = "model_deployments"
    model_name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(80))
    alias: Mapped[str] = mapped_column(String(80))
    run_id: Mapped[str] = mapped_column(String(100))


class IngestionRun(Identity, Base):
    __tablename__ = "ingestion_runs"
    mode: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="running")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    counts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    errors: Mapped[list[str]] = mapped_column(JSON, default=list)
