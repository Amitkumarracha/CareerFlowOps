from datetime import UTC, datetime
from typing import Any

from ingestion.base import RawJob, SourceAdapter
from ingestion.normalize import plain_text


class LeverAdapter(SourceAdapter):
    @property
    def url(self) -> str:
        return f"https://api.lever.co/v0/postings/{self.source.board}?mode=json"

    def records(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, list):
            raise ValueError("Expected Lever postings list")
        return payload

    def parse(self, item: dict[str, Any]) -> RawJob:
        categories = item.get("categories") or {}
        description = item.get("descriptionPlain") or plain_text(item.get("description") or "")
        description += " " + " ".join(
            plain_text(section.get("content") or "") for section in item.get("lists", [])
        )
        return RawJob(
            source_name="lever",
            source_job_id=item["id"],
            source_url=item["hostedUrl"],
            apply_url=item["applyUrl"],
            company=self.source.company,
            title=item["text"],
            location=categories.get("location") or "Unknown",
            description=description.strip(),
            employment_type=categories.get("commitment"),
            remote={"remote": True, "on-site": False, "hybrid": False}.get(
                item.get("workplaceType")
            ),
            posted_at=datetime.fromtimestamp(item["createdAt"] / 1000, UTC)
            if item.get("createdAt")
            else None,
            payload=item,
        )
