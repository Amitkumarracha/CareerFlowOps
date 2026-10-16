from typing import Any

from ingestion.base import RawJob, SourceAdapter
from ingestion.normalize import plain_text


class AshbyAdapter(SourceAdapter):
    @property
    def url(self) -> str:
        return f"https://api.ashbyhq.com/posting-api/job-board/{self.source.board}"

    def records(self, payload: Any) -> list[dict[str, Any]]:
        return [item for item in payload["jobs"] if item.get("isListed", True)]

    def parse(self, item: dict[str, Any]) -> RawJob:
        return RawJob(
            source_name="ashby",
            source_job_id=item["id"],
            source_url=item["jobUrl"],
            apply_url=item["applyUrl"],
            company=self.source.company,
            title=item["title"],
            location=item.get("location") or "Unknown",
            description=item.get("descriptionPlain")
            or plain_text(item.get("descriptionHtml") or ""),
            employment_type=item.get("employmentType"),
            remote=item.get("isRemote"),
            posted_at=item.get("publishedAt"),
            payload=item,
        )
