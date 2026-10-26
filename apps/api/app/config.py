from functools import lru_cache
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_env: Literal["development", "test", "production"] = "development"
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
    ranking_algorithm: str = "hybrid"
    use_model_registry: bool = False
    model_bundle_path: Path | None = None
    prometheus_enabled: bool = True
    log_level: str = "INFO"

    @model_validator(mode="after")
    def production_configuration(self) -> Self:
        if self.app_env != "production":
            return self
        if not self.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("Production requires PostgreSQL with the psycopg driver")
        if self.model_bundle_path is None:
            raise ValueError("Production requires MODEL_BUNDLE_PATH; local fallback is disabled")
        tokens = [self.candidate_api_token, self.admin_api_token]
        if any(len(token) < 32 or "CHANGE_ME" in token for token in tokens):
            raise ValueError(
                "Production access tokens must be generated and at least 32 characters"
            )
        if tokens[0] == tokens[1]:
            raise ValueError("Candidate and admin tokens must differ")
        for origin in self.cors_origins.split(","):
            parsed = urlsplit(origin)
            if (
                not parsed.hostname
                or "*" in parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
                or not (
                    parsed.scheme == "https"
                    or (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"})
                )
            ):
                raise ValueError("Production CORS origins must be HTTPS or loopback HTTP origins")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
