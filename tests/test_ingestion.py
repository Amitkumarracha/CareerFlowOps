import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.app.models.entities import Job, JobSourceOccurrence
from ingestion.base import SourceConfig
from ingestion.runner import ADAPTERS, run_ingestion, sources


@pytest.mark.parametrize("config", sources())
def test_adapter_frozen_response(config: SourceConfig) -> None:
    payload = json.loads(Path(f"data/samples/{config.name}.json").read_text())
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as client:
        adapter = ADAPTERS[config.name](config, client)
        records = adapter.records(adapter.fetch())
        assert len(records) == 10
        for record in records:
            parsed = adapter.parse(record)
            assert str(parsed.apply_url).startswith("https://")
            assert parsed.source_job_id and parsed.title and parsed.payload


def test_idempotent_raw_and_provenance(db: Session, tmp_path) -> None:
    first = run_ingestion(db, tmp_path, fixture=True)
    assert first.status == "succeeded"
    count = db.scalar(select(func.count()).select_from(Job))
    hashes = set(db.scalars(select(JobSourceOccurrence.source_payload_hash)))
    second = run_ingestion(db, tmp_path, fixture=True)
    assert second.status == "succeeded"
    assert db.scalar(select(func.count()).select_from(Job)) == count
    assert db.scalar(select(func.count()).select_from(JobSourceOccurrence)) == 30
    assert set(db.scalars(select(JobSourceOccurrence.source_payload_hash))) == hashes
    assert len(list((tmp_path / "raw").glob("*/*.json"))) >= 30
    assert not any(db.scalars(select(JobSourceOccurrence.verified_at)))


def test_source_failure_does_not_discard_success(db: Session, tmp_path) -> None:
    def response(request: httpx.Request) -> httpx.Response:
        if "lever" in str(request.url):
            return httpx.Response(403)
        name = "greenhouse" if "greenhouse" in str(request.url) else "ashby"
        return httpx.Response(200, json=json.loads(Path(f"data/samples/{name}.json").read_text()))

    with httpx.Client(transport=httpx.MockTransport(response)) as client:
        run = run_ingestion(db, tmp_path, client=client)
    assert run.status == "partial"
    assert run.counts["normalized"] == 20
    assert run.errors == ["lever: HTTPStatusError"]
