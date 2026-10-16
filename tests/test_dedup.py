import json
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.app.models.entities import Job, JobSource, JobSourceOccurrence
from ingestion.base import SourceConfig
from ingestion.greenhouse import GreenhouseAdapter
from ingestion.normalize import fingerprint
from ingestion.runner import upsert


def test_fingerprint_normalization_and_cross_source_provenance(db: Session, tmp_path) -> None:
    payload = json.loads(Path("data/samples/greenhouse.json").read_text())["jobs"][0]
    with httpx.Client() as client:
        item = GreenhouseAdapter(
            SourceConfig(name="greenhouse", board="stripe", company="Stripe"), client
        ).parse(payload)
    altered = item.model_copy(update={"title": item.title.upper() + "  ", "source_name": "lever"})
    assert fingerprint(item) == fingerprint(altered)
    for name, raw in [("greenhouse", item), ("lever", altered)]:
        source = JobSource(name=name, board="test")
        db.add(source)
        db.flush()
        upsert(db, raw, source, tmp_path, True)
    db.commit()
    assert db.scalar(select(func.count()).select_from(Job)) == 1
    assert db.scalar(select(func.count()).select_from(JobSourceOccurrence)) == 2
    # Different location must not merge.
    assert fingerprint(item.model_copy(update={"location": "Different city"})) != fingerprint(item)


def test_admin_access_and_dedup_debug(client) -> None:
    assert client.get("/api/admin/dedup").status_code == 401
    result = client.post(
        "/api/admin/ingestion/run",
        json={"mode": "fixture"},
        headers={"Authorization": "Bearer test-admin-token"},
    )
    assert result.status_code == 200
    debug = client.get(
        "/api/admin/dedup", headers={"Authorization": "Bearer test-admin-token"}
    ).json()
    assert sum(job["source_occurrences"] for job in debug["jobs"]) == 30
