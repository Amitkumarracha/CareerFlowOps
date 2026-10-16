from typing import Any

from ingestion.base import RawJob, SourceAdapter
from ingestion.normalize import plain_text


class GreenhouseAdapter(SourceAdapter):
    @property
    def url(self) -> str:
        return f"https://boards-api.greenhouse.io/v1/boards/{self.source.board}/jobs?content=true"

    def records(self, payload: Any) -> list[dict[str, Any]]:
        return payload["jobs"]

    def parse(self, item: dict[str, Any]) -> RawJob:
        location = (item.get("location") or {}).get("name") or "Unknown"
        return RawJob(
            source_name="greenhouse",
            source_job_id=str(item["id"]),
            source_url=item["absolute_url"],
            apply_url=item["absolute_url"],
            company=self.source.company,
            title=item["title"],
            location=location,
            description=plain_text(item.get("content") or ""),
            remote=True if "remote" in location.casefold() else None,
            posted_at=item.get("first_published"),
            payload=item,
        )
