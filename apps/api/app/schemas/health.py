from pydantic import BaseModel


class Health(BaseModel):
    status: str
    service: str = "careerflowops-api"
    model_version: str | None = None
    algorithm: str | None = None
    bundle_id: str | None = None
