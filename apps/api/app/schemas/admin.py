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
