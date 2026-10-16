from pydantic import BaseModel


class NamedCount(BaseModel):
    name: str
    count: int


class JobCandidates(BaseModel):
    job_id: str
    title: str
    potentially_matched_candidates: int
    eligibility_unknown_candidates: int


class AnalyticsOut(BaseModel):
    active_students: int
    active_opportunities: int
    new_jobs_today: int
    applications: int
    interviews: int
    offers: int
    top_companies: list[NamedCount]
    top_job_categories: list[NamedCount]
    skill_gaps: list[NamedCount]
    placement_funnel: dict[str, int]
    job_matches: list[JobCandidates]
    scope: str


class ExperimentResult(BaseModel):
    algorithm: str
    split: str
    metrics: dict[str, float]


class EvaluationOut(BaseModel):
    dataset_version: str
    labels_description: str
    selected_algorithm: str
    results: list[ExperimentResult]


class RegistryOut(BaseModel):
    model_name: str
    version: str
    alias: str
    run_id: str


class MlopsOut(BaseModel):
    evaluation: EvaluationOut | None
    registry: RegistryOut | None
    status_message: str
