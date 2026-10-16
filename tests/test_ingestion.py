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


def test_fixture_never_overwrites_newer_live_occurrence(db: Session, tmp_path) -> None:
    from apps.api.app.models.entities import JobSource
    from ingestion.runner import upsert

    config = sources()[0]
    with httpx.Client() as client:
        adapter = ADAPTERS[config.name](config, client)
        original = adapter.parse(
            adapter.records(json.loads(Path("data/samples/greenhouse.json").read_text()))[0]
        )
    source = JobSource(name=config.name, board=config.board)
    db.add(source)
    db.flush()
    upsert(db, original, source, tmp_path, True)
    updated = original.model_copy(
        update={
            "description": "Updated live description",
            "payload": {**original.payload, "content": "Updated live description"},
        }
    )
    upsert(db, updated, source, tmp_path, False)
    db.flush()
    current_hash = db.scalars(select(JobSourceOccurrence.source_payload_hash)).one()
    upsert(db, original, source, tmp_path, True)
    db.commit()
    occurrence = db.scalars(select(JobSourceOccurrence)).one()
    assert occurrence.source_payload_hash == current_hash
    assert occurrence.verification_status == "official_api" and occurrence.verified_at is not None
    assert db.scalars(select(Job.description)).one() == "Updated live description"


def test_source_title_edits_preserve_canonical_identity(db: Session, tmp_path) -> None:
    from apps.api.app.models.entities import JobSource
    from ingestion.runner import upsert

    config = sources()[0]
    with httpx.Client() as client:
        adapter = ADAPTERS[config.name](config, client)
        original = adapter.parse(
            adapter.records(json.loads(Path("data/samples/greenhouse.json").read_text()))[0]
        )
    source = JobSource(name=config.name, board=config.board)
    db.add(source)
    db.flush()
    upsert(db, original, source, tmp_path, False)
    identity = db.scalars(select(Job.id)).one()
    edited = original.model_copy(update={"title": "Updated role title", "location": "Updated city"})
    upsert(db, edited, source, tmp_path, False)
    db.commit()
    job = db.scalars(select(Job)).one()
    assert (
        job.id == identity and job.title == "Updated role title" and job.location == "Updated city"
    )
    assert job.occurrences[0].job_id == identity

    collision = edited.model_copy(update={"source_job_id": "second", "title": "Taken title"})
    upsert(db, collision, source, tmp_path, False)
    upsert(db, edited.model_copy(update={"title": "Taken title"}), source, tmp_path, False)
    db.commit()
    assert db.scalar(select(func.count()).select_from(Job)) == 2
    assert db.get(Job, identity).title == "Taken title"
    original_occurrence = db.scalar(
        select(JobSourceOccurrence).where(
            JobSourceOccurrence.source_job_id == original.source_job_id
        )
    )
    assert original_occurrence.job_id == identity
