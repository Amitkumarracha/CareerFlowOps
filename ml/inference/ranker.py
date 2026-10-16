import math
import os
import re
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ml.features.skills import extract_skills, normalize_skills

MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_weights(path: Path = Path("params.yaml"), environment: bool = True) -> dict[str, float]:
    weights = {
        key: float(value) for key, value in yaml.safe_load(path.read_text())["ranking"].items()
    }
    if environment:
        for key in weights:
            weights[key] = float(os.getenv(f"MATCH_{key.upper()}_WEIGHT", weights[key]))
    if (
        set(weights) != {"semantic", "skill", "eligibility", "location", "freshness"}
        or any(not math.isfinite(value) or value < 0 for value in weights.values())
        or not math.isclose(sum(weights.values()), 1.0)
    ):
        raise ValueError("Ranking weights must be finite, nonnegative and sum to one")
    return weights


def profile_text(profile: dict[str, Any]) -> str:
    return (
        " ".join(
            str(profile.get(key) or "")
            for key in ["summary", "education", "experience", "projects", "certifications"]
        )
        + " "
        + " ".join(profile.get("skills", []))
    )


def job_text(job: dict[str, Any]) -> str:
    return str(job.get("title", "")) + " " + str(job.get("description", ""))


@lru_cache(maxsize=4)
def tfidf_index(documents: tuple[str, ...]) -> tuple[TfidfVectorizer, Any]:
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=20000, stop_words="english")
    return vectorizer, vectorizer.fit_transform(documents)


@lru_cache(maxsize=2)
def embedding_model(model_name: str = MODEL, local_only: bool = True) -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, device="cpu", local_files_only=local_only)


@lru_cache(maxsize=2)
def embeddings(documents: tuple[str, ...], model_name: str) -> np.ndarray:
    return embedding_model(model_name).encode(
        list(documents), normalize_embeddings=True, show_progress_bar=False
    )


def semantic_scores(
    text: str, documents: tuple[str, ...], algorithm: str, model_name: str, allow_fallback: bool
) -> tuple[list[float], str, str | None]:
    if algorithm == "tfidf":
        backend = "tfidf"
        fallback = None
    else:
        try:
            model = embedding_model(model_name)
            query = model.encode([text], normalize_embeddings=True, show_progress_bar=False)
            scores = np.clip(embeddings(documents, model_name) @ query[0], 0, 1)
            return scores.tolist(), "sentence_transformer", None
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            if not allow_fallback:
                raise RuntimeError(
                    "SentenceTransformer is unavailable; download the documented model first"
                ) from exc
            backend = "tfidf"
            fallback = (
                "Embedding model unavailable locally; semantic component uses the TF-IDF fallback."
            )
    try:
        vectorizer, matrix = tfidf_index(documents)
        scores = cosine_similarity(vectorizer.transform([text]), matrix)[0]
        return np.clip(scores, 0, 1).tolist(), backend, fallback
    except ValueError:
        return [0.0] * len(documents), backend, fallback


def eligibility(profile: dict[str, Any], job: dict[str, Any]) -> tuple[float, str]:
    required = re.search(
        r"\b(\d{1,2})\+?\s+years?\s+(?:of\s+)?(?:relevant\s+|professional\s+)?experience",
        str(job.get("description", "")),
        re.I,
    )
    years = profile.get("experience_years")
    if not required or years is None:
        return (
            0.5,
            "Eligibility unknown: experience evidence is missing. "
            "Confirm requirements on the official posting.",
        )
    minimum = int(required.group(1))
    if float(years) >= minimum:
        return (
            1.0,
            f"Your {years:g} years meet the stated {minimum}-year minimum. "
            "Other eligibility requirements are unverified.",
        )
    return (
        0.0,
        f"Experience gap: the posting mentions {minimum}+ years; your profile lists {years:g}. "
        "Other eligibility requirements are unverified.",
    )


def rank_jobs(
    profile: dict[str, Any],
    jobs: list[dict[str, Any]],
    algorithm: str = "hybrid",
    weights: dict[str, float] | None = None,
    as_of: datetime | None = None,
    model_name: str = MODEL,
    allow_fallback: bool = True,
    model_version: str = "local-v1",
) -> list[dict[str, Any]]:
    if algorithm not in {"tfidf", "sentence_transformer", "hybrid"}:
        raise ValueError("Unsupported ranking algorithm")
    if not jobs:
        return []
    weights = weights or load_weights()
    as_of = as_of or datetime.now(UTC)
    semantic, backend, fallback = semantic_scores(
        profile_text(profile),
        tuple(job_text(job) for job in jobs),
        algorithm,
        model_name,
        allow_fallback,
    )
    candidate_skills = set(normalize_skills(profile.get("skills", [])))
    results: list[dict[str, Any]] = []
    for job, similarity in zip(jobs, semantic, strict=True):
        job_skills = set(job.get("skills") or extract_skills(job_text(job)))
        matched = sorted(candidate_skills & job_skills)
        missing = sorted(job_skills - candidate_skills)
        skill_score = len(matched) / len(job_skills) if job_skills else 0.5
        eligibility_score, eligibility_explanation = eligibility(profile, job)
        location = str(profile.get("location") or "").strip().casefold()
        location_score = (
            1.0
            if job.get("remote") is True
            or (location and location in str(job.get("location", "")).casefold())
            else 0.5
            if not location or job.get("location") in {None, "Unknown"}
            else 0.0
        )
        posted = job.get("posted_at")
        if posted:
            date = (
                datetime.fromisoformat(str(posted).replace("Z", "+00:00"))
                if isinstance(posted, str)
                else posted
            )
            date = date.replace(tzinfo=UTC) if date.tzinfo is None else date
            age = max(0, (as_of - date).total_seconds() / 86400)
            freshness = math.exp(-age / 30)
        else:
            freshness = 0.5
        components = {
            "semantic": float(similarity),
            "skill": skill_score,
            "eligibility": eligibility_score,
            "location": location_score,
            "freshness": freshness,
        }
        overall = (
            sum(weights[key] * value for key, value in components.items())
            if algorithm == "hybrid"
            else float(similarity)
        )
        label = f"hybrid_{backend}" if algorithm == "hybrid" else backend
        results.append(
            {
                "job_id": job["id"],
                "overall_score": round(overall, 6),
                **{f"{key}_score": round(value, 6) for key, value in components.items()},
                "matched_skills": matched,
                "missing_skills": missing,
                "explanation": [
                    f"{len(matched)} of {len(job_skills)} known job skills appear in your profile."
                    if job_skills
                    else "The posting does not identify known skills; skill fit is unknown.",
                    eligibility_explanation,
                    "Location is compatible."
                    if location_score == 1
                    else "Location fit is unknown."
                    if location_score == 0.5
                    else "Location differs from your profile.",
                    "Posting date is unknown; freshness is neutral."
                    if not posted
                    else "Freshness is based on the official posting timestamp.",
                    "Scores compare content and known skills; they do not predict hiring outcomes.",
                ],
                "algorithm": label,
                "model_version": model_version,
                "fallback_reason": fallback,
            }
        )
    return sorted(results, key=lambda result: (-result["overall_score"], result["job_id"]))
