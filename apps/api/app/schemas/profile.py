from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ml.features.skills import normalize_skills


class ProfileData(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    name: str | None = Field(None, max_length=250)
    email: str | None = Field(None, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    phone: str | None = Field(None, max_length=80)
    location: str | None = Field(None, max_length=250)
    experience_years: float | None = Field(None, ge=0, le=80, allow_inf_nan=False)
    skills: list[str] = Field(default_factory=list, max_length=100)
    summary: str = Field("", max_length=10000)
    education: str = Field("", max_length=10000)
    experience: str = Field("", max_length=10000)
    projects: str = Field("", max_length=10000)
    certifications: str = Field("", max_length=10000)

    @field_validator("skills")
    @classmethod
    def skills_length(cls, skills: list[str]) -> list[str]:
        if any(len(skill) > 100 for skill in skills):
            raise ValueError("Each skill must be 100 characters or fewer")
        return normalize_skills(skills)


class ResumeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    filename: str
    created_at: datetime


class ResumeOut(ResumeSummary):
    extracted_text: str
    extracted_profile: ProfileData
