from abc import ABC, abstractmethod
from datetime import datetime
from time import sleep
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, HttpUrl, field_validator


class SourceConfig(BaseModel):
    name: Literal["greenhouse", "lever", "ashby"]
    board: str = Field(pattern=r"^[A-Za-z0-9_-]{1,120}$")
    company: str = Field(min_length=1, max_length=250)


class RawJob(BaseModel):
    source_name: str
    source_job_id: str = Field(min_length=1)
    source_url: HttpUrl
    apply_url: HttpUrl
    company: str = Field(min_length=1)
    title: str = Field(min_length=1)
    location: str = "Unknown"
    description: str = ""
    employment_type: str | None = None
    remote: bool | None = None
    posted_at: datetime | None = None
    payload: dict[str, Any]

    @field_validator("title", "company")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Must not be blank")
        return value.strip()


class SourceAdapter(ABC):
    def __init__(self, source: SourceConfig, client: httpx.Client) -> None:
        self.source = source
        self.client = client

    @property
    @abstractmethod
    def url(self) -> str: ...

    def fetch(self) -> Any:
        for attempt in range(3):
            response = self.client.get(self.url)
            if response.status_code not in {429, 502, 503, 504} or attempt == 2:
                response.raise_for_status()
                return response.json()
            try:
                delay = max(float(response.headers.get("Retry-After", 2**attempt)), 0)
            except ValueError:
                response.raise_for_status()
                raise
            if delay > 30:
                response.raise_for_status()
            sleep(delay)
        raise RuntimeError("Source retries exhausted")

    @abstractmethod
    def records(self, payload: Any) -> list[dict[str, Any]]: ...

    @abstractmethod
    def parse(self, item: dict[str, Any]) -> RawJob: ...
