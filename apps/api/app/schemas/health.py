from pydantic import BaseModel


class Health(BaseModel):
    status: str
    service: str = "careerflowops-api"
