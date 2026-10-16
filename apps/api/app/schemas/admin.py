from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class IngestionRequest(BaseModel):
    mode: Literal["live", "fixture"] = "live"


class IngestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    mode: str
    status: str
    counts: dict[str, Any]
    errors: list[str]
    created_at: datetime
    finished_at: datetime | None


class DedupJob(BaseModel):
    id: str
    title: str
    fingerprint: str
    source_occurrences: int
    sources: list[str]


class DuplicatePair(BaseModel):
    left_id: str
    right_id: str
    similarity: float


class DedupResponse(BaseModel):
    jobs: list[DedupJob]
    possible_duplicates: list[DuplicatePair]
    scope: str = "Most recent 200 jobs; fuzzy pairs are diagnostic only"
