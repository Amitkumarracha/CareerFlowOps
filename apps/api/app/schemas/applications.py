from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.api.app.schemas.jobs import JobOut

Status = Literal["SAVED", "APPLIED", "INTERVIEW", "OFFER", "REJECTED", "WITHDRAWN"]


class SaveRequest(BaseModel):
    job_id: str = Field(min_length=1, max_length=36)


class ApplicationCreate(SaveRequest):
    status: Status = "SAVED"
    notes: str = Field("", max_length=5000)


class ApplicationUpdate(BaseModel):
    status: Status
    notes: str = Field("", max_length=5000)


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: Status
    notes: str
    changed_at: datetime


class ApplicationOut(BaseModel):
    id: str
    job: JobOut
    status: Status
    notes: str
    updated_at: datetime
    history: list[HistoryOut]


class SavedOut(BaseModel):
    id: str
    job: JobOut
    created_at: datetime
