import hashlib
import json
import os
from pathlib import Path
from typing import Any

import httpx
import yaml
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from apps.api.app.models.entities import (
    Company,
    IngestionRun,
    Job,
    JobSkill,
    JobSource,
    JobSourceOccurrence,
    now,
)
from ingestion.ashby import AshbyAdapter
from ingestion.base import RawJob, SourceAdapter, SourceConfig
from ingestion.greenhouse import GreenhouseAdapter
from ingestion.lever import LeverAdapter
from ingestion.normalize import experience_level, fingerprint, normalized
from ml.features.skills import extract_skills

ADAPTERS: dict[str, type[SourceAdapter]] = {
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "ashby": AshbyAdapter,
}


def sources(path: Path = Path("sources.yaml")) -> list[SourceConfig]:
    return [
        SourceConfig.model_validate(item)
        for item in yaml.safe_load(path.read_text())["sources"]
        if os.getenv("INGEST_" + item["name"].upper(), "true").casefold() == "true"
    ]


def archive(payload: Any, directory: Path) -> tuple[str, str]:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{digest}.json"
    if not target.exists():
        target.write_bytes(encoded)
    return digest, str(target)


def upsert(db: Session, item: RawJob, source: JobSource, raw_dir: Path, fixture: bool) -> bool:
    digest, raw_path = archive(item.payload, raw_dir)
    occurrence = db.scalar(
        select(JobSourceOccurrence).where(
            JobSourceOccurrence.source_id == source.id,
            JobSourceOccurrence.source_job_id == item.source_job_id,
        )
    )
    canonical = db.scalar(select(Job).where(Job.fingerprint == fingerprint(item)))
    duplicate = occurrence is None and canonical is not None
    if canonical is None:
        company = db.scalar(select(Company).where(Company.name == normalized(item.company)))
        if company is None:
            company = Company(name=normalized(item.company))
            db.add(company)
            db.flush()
        canonical = Job(
            company_id=company.id,
            title=item.title,
            location=item.location,
            fingerprint=fingerprint(item),
        )
        db.add(canonical)
        db.flush()
    canonical.description = item.description
    canonical.employment_type = (
        item.employment_type.casefold().replace("-", " ") if item.employment_type else None
    )
    canonical.experience_level = experience_level(item.title)
    canonical.remote = item.remote
    canonical.posted_at = item.posted_at
    canonical.last_seen_at = now()
    canonical.skills = [
        JobSkill(skill=skill) for skill in extract_skills(item.description + " " + item.title)
    ]
    if occurrence is None:
        occurrence = JobSourceOccurrence(
            source_id=source.id, source_name=item.source_name, source_job_id=item.source_job_id
        )
        db.add(occurrence)
    occurrence.job_id = canonical.id
    occurrence.source_url = str(item.source_url)
    occurrence.apply_url = str(item.apply_url)
    occurrence.source_payload_hash = digest
    occurrence.raw_path = raw_path
    occurrence.source_posted_at = item.posted_at
    occurrence.last_seen_at = now()
    # A historical fixture never claims current verification.
    if not fixture:
        occurrence.verified_at = now()
        occurrence.verification_status = "official_api"
    elif occurrence.verification_status != "official_api":
        occurrence.verification_status = "snapshot"
    db.flush()
    return duplicate


def run_ingestion(
    db: Session, data_dir: Path, fixture: bool = False, client: httpx.Client | None = None
) -> IngestionRun:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        if not db.scalar(text("SELECT pg_try_advisory_xact_lock(73419281)")):
            raise RuntimeError("An ingestion run is already active")
    run = IngestionRun(mode="fixture" if fixture else "live", counts={}, errors=[])
    db.add(run)
    db.flush()
    counts: dict[str, Any] = {"fetched": 0, "normalized": 0, "duplicates": 0, "by_source": {}}
    errors: list[str] = []
    owned = client is None
    client = client or httpx.Client(
        timeout=30,
        follow_redirects=False,
        headers={"User-Agent": "CareerFlowOps/0.1 public-job-discovery"},
    )
    try:
        for config in sources():
            adapter = ADAPTERS[config.name](config, client)
            try:
                payload = (
                    json.loads((Path("data/samples") / f"{config.name}.json").read_text())
                    if fixture
                    else adapter.fetch()
                )
                archive(payload, data_dir / "raw" / config.name)
                records = adapter.records(payload)
                if not isinstance(records, list):
                    raise ValueError("Invalid source response")
                counts["by_source"][config.name] = len(records)
                counts["fetched"] += len(records)
                source = db.scalar(
                    select(JobSource).where(
                        JobSource.name == config.name, JobSource.board == config.board
                    )
                )
                if source is None:
                    source = JobSource(name=config.name, board=config.board)
                    db.add(source)
                    db.flush()
                for record in records:
                    try:
                        with db.begin_nested():
                            counts["duplicates"] += int(
                                upsert(
                                    db,
                                    adapter.parse(record),
                                    source,
                                    data_dir / "raw" / config.name,
                                    fixture,
                                )
                            )
                            counts["normalized"] += 1
                    except (ValidationError, KeyError, ValueError, TypeError):
                        errors.append(f"{config.name}: invalid posting skipped")
            except (httpx.HTTPError, ValueError, KeyError, TypeError, OSError) as exc:
                errors.append(f"{config.name}: {type(exc).__name__}")
    finally:
        if owned:
            client.close()
    run.status = (
        "partial" if errors and counts["normalized"] else "failed" if errors else "succeeded"
    )
    run.errors = errors
    run.counts = counts
    run.finished_at = now()
    db.commit()
    return run
