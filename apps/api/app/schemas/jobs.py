from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OccurrenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source_name: str
    source_job_id: str
    source_url: str
    apply_url: str
    source_payload_hash: str
    first_seen_at: datetime
    last_seen_at: datetime
    source_posted_at: datetime | None
    verified_at: datetime | None
    verification_status: str


class JobOut(BaseModel):
    id: str
    title: str
    company: str
    location: str
    description: str
    employment_type: str | None
    experience_level: str | None
    remote: bool | None
    posted_at: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime
    skills: list[str]
    apply_url: str | None
    sources: list[OccurrenceOut]


class JobList(BaseModel):
    items: list[JobOut]
    total: int
    limit: int
    offset: int
