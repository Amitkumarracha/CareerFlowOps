import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.app.db import get_db
from apps.api.app.dependencies.auth import admin
from apps.api.app.models.entities import Application, Candidate, CandidateProfile, Company, Job
from apps.api.app.schemas.analytics import AnalyticsOut, MlopsOut
from apps.api.app.schemas.applications import Status
from ml.inference.ranker import eligibility

router = APIRouter(prefix="/api", tags=["analytics"], dependencies=[Depends(admin)])
STATUSES: list[Status] = ["SAVED", "APPLIED", "INTERVIEW", "OFFER", "REJECTED", "WITHDRAWN"]


def named(counter: Counter, limit: int = 10) -> list[dict]:
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


@router.get("/tpo", response_model=AnalyticsOut)
def tpo(db: Session = Depends(get_db)) -> dict:
    total_jobs = db.scalar(select(func.count()).select_from(Job).where(Job.active.is_(True))) or 0
    students = (
        db.scalar(
            select(func.count())
            .select_from(CandidateProfile)
            .join(Candidate)
            .where(Candidate.active.is_(True))
        )
        or 0
    )
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    new_today = (
        db.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.active.is_(True), Job.created_at >= today)
        )
        or 0
    )
    counts = dict(
        db.execute(select(Application.status, func.count()).group_by(Application.status)).all()
    )
    companies = db.execute(
        select(Company.name, func.count(Job.id))
        .join(Job)
        .where(Job.active.is_(True))
        .group_by(Company.name)
        .order_by(func.count(Job.id).desc(), Company.name)
        .limit(10)
    ).all()
    profiles = list(
        db.scalars(
            select(CandidateProfile)
            .join(Candidate)
            .where(Candidate.active.is_(True))
            .order_by(CandidateProfile.candidate_id)
            .limit(500)
        )
    )
    jobs = list(
        db.scalars(
            select(Job)
            .where(Job.active.is_(True))
            .order_by(Job.last_seen_at.desc(), Job.id)
            .limit(100)
        )
    )
    gaps: Counter = Counter()
    categories: Counter = Counter()
    matches = []
    for job in jobs:
        skills = {skill.skill for skill in job.skills}
        matched = 0
        unknown = 0
        category = next(
            (
                label
                for pattern, label in [
                    (r"engineer|developer", "Engineering"),
                    (r"sales|account executive", "Sales"),
                    (r"support", "Support"),
                    (r"product manager", "Product management"),
                    (r"administrat|business partner", "Operations"),
                ]
                if re.search(pattern, job.title, re.I)
            ),
            "Other",
        )
        categories[category] += 1
        for profile in profiles:
            candidate_skills = set(profile.skills)
            if not candidate_skills:
                continue
            gaps.update(skills - candidate_skills)
            score, _ = eligibility(
                {"experience_years": profile.experience_years}, {"description": job.description}
            )
            if skills and len(skills & candidate_skills) / len(skills) >= 0.5 and score != 0:
                matched += 1
                unknown += int(score == 0.5)
        matches.append(
            {
                "job_id": job.id,
                "title": job.title,
                "potentially_matched_candidates": matched,
                "eligibility_unknown_candidates": unknown,
            }
        )
    return {
        "active_students": students,
        "active_opportunities": total_jobs,
        "new_jobs_today": new_today,
        "applications": sum(counts.values()),
        "interviews": counts.get("INTERVIEW", 0),
        "offers": counts.get("OFFER", 0),
        "top_companies": [{"name": name, "count": count} for name, count in companies],
        "top_job_categories": named(categories),
        "skill_gaps": named(gaps),
        "placement_funnel": {status: counts.get(status, 0) for status in STATUSES},
        "job_matches": matches,
        "scope": (
            "Global persisted counts; breakdown: latest 100 jobs, first 500 active profiles. "
            "Skill gaps count candidate-job pairs."
        ),
    }


@router.get("/mlops", response_model=MlopsOut)
def mlops() -> dict:
    try:
        evaluation_path = Path("ml/artifacts/evaluation.json")
        registry_path = Path("ml/artifacts/registry.json")
        evaluation = json.loads(evaluation_path.read_text()) if evaluation_path.exists() else None
        registry = json.loads(registry_path.read_text()) if registry_path.exists() else None
    except (OSError, ValueError) as exc:
        raise HTTPException(
            503, "Saved ML artifacts are unreadable; rerun the documented pipeline."
        ) from exc
    return {
        "evaluation": evaluation,
        "registry": registry,
        "status_message": (
            "Saved evaluation and registration artifacts. "
            "Restart the API after promoting a production alias."
        )
        if evaluation
        else "No evaluation artifact yet. Run make reproduce after starting PostgreSQL and MLflow.",
    }
