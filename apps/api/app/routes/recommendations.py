from pathlib import Path
from time import perf_counter
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.config import get_settings
from apps.api.app.db import get_db
from apps.api.app.dependencies.auth import candidate
from apps.api.app.models.entities import CandidateProfile, Job
from apps.api.app.observability import INFERENCE_LATENCY, MODEL, RECOMMENDATIONS, SCORES
from apps.api.app.schemas.profile import ProfileData
from apps.api.app.schemas.recommendations import MatchOut
from apps.api.app.services.jobs import serialize_job
from ml.inference.bundle import load_bundle
from ml.inference.ranker import rank_jobs
from ml.registry.client import predict_registered

router = APIRouter(tags=["recommendations"])


@router.get("/api/jobs/recommended", response_model=list[MatchOut])
def recommended(
    algorithm: Literal["tfidf", "sentence_transformer", "hybrid"] | None = None,
    min_score: float = Query(0, ge=0, le=1),
    limit: int = Query(50, ge=1, le=100),
    candidate_id: str = Depends(candidate),
    db: Session = Depends(get_db),
) -> list[dict]:
    RECOMMENDATIONS.inc()
    profile = db.get(CandidateProfile, candidate_id)
    if profile is None or not (
        profile.skills or profile.summary or profile.experience or profile.projects
    ):
        raise HTTPException(
            422, "Add your skills or upload a resume before requesting recommendations."
        )
    # shortcut: cap the candidate set at 1000 jobs; add indexed retrieval before larger deployments.
    jobs = list(
        db.scalars(
            select(Job)
            .where(Job.active.is_(True))
            .order_by(Job.last_seen_at.desc(), Job.id)
            .limit(1000)
        )
    )
    if not jobs:
        return []
    job_data = [serialize_job(job).model_dump(mode="json") for job in jobs]
    lookup = {job["id"]: job for job in job_data}
    profile_data = ProfileData.model_validate(profile).model_dump()
    settings = get_settings()
    start = perf_counter()
    registry_fallback: str | None = None
    if settings.model_bundle_path is not None:
        try:
            bundle = load_bundle(str(settings.model_bundle_path))
            if algorithm is not None and algorithm != bundle.config["algorithm"]:
                raise HTTPException(422, "Production serves only the selected release algorithm")
            predictions = bundle.predict(profile_data, job_data)
        except RuntimeError as exc:
            raise HTTPException(503, "Production model unavailable") from exc
    elif settings.use_model_registry and algorithm is None:
        try:
            predictions = predict_registered(
                settings.mlflow_tracking_uri,
                f"models:/{settings.mlflow_model_name}@{settings.mlflow_model_alias}",
                profile_data,
                job_data,
            )
        except Exception:
            # External registry failures must not prevent local recommendations.
            registry_fallback = (
                "Production registry unavailable; using the documented local model fallback."
            )
            predictions = []
    else:
        predictions = []
    if not predictions:
        local_model = Path("ml/artifacts/sentence-transformer")
        predictions = rank_jobs(
            profile_data,
            job_data,
            algorithm=algorithm or settings.ranking_algorithm,
            model_name=str(local_model)
            if local_model.is_dir()
            else settings.sentence_transformer_model,
        )
    INFERENCE_LATENCY.observe(perf_counter() - start)
    if predictions:
        MODEL.info(
            {"algorithm": predictions[0]["algorithm"], "version": predictions[0]["model_version"]}
        )
    output = []
    for prediction in predictions:
        if prediction["overall_score"] < min_score:
            continue
        data = dict(prediction)
        data["job"] = lookup[data.pop("job_id")]
        if registry_fallback:
            data["fallback_reason"] = " ".join(
                filter(None, [registry_fallback, data.get("fallback_reason")])
            )
        SCORES.observe(data["overall_score"])
        output.append(data)
    return output[:limit]
