from pydantic import BaseModel, Field

from apps.api.app.schemas.jobs import JobOut


class MatchOut(BaseModel):
    job: JobOut
    overall_score: float = Field(ge=0, le=1)
    semantic_score: float = Field(ge=0, le=1)
    skill_score: float = Field(ge=0, le=1)
    eligibility_score: float = Field(ge=0, le=1)
    location_score: float = Field(ge=0, le=1)
    freshness_score: float = Field(ge=0, le=1)
    matched_skills: list[str]
    missing_skills: list[str]
    explanation: list[str]
    algorithm: str
    model_version: str
    fallback_reason: str | None
