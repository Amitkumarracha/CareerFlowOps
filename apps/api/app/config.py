from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "sqlite:///./careerflowops.db"
    cors_origins: str = "http://localhost:5173"
    candidate_api_token: str = ""
    admin_api_token: str = ""
    data_dir: Path = Path("data")
    max_resume_bytes: int = 5 * 1024 * 1024
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_model_name: str = "careerflowops-ranker"
    mlflow_model_alias: str = "production"
    sentence_transformer_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ranking_algorithm: str = "tfidf"
    use_model_registry: bool = False
    prometheus_enabled: bool = True
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
