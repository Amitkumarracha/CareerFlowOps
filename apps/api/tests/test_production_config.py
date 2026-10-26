import pytest
from pydantic import ValidationError

from apps.api.app.config import Settings


def production(**overrides) -> Settings:
    return Settings(
        _env_file=None,
        **{
            "app_env": "production",
            "database_url": "postgresql+psycopg://operator:private@postgres/careerflowops",
            "model_bundle_path": "/app/ml/artifacts/production",
            "candidate_api_token": "a" * 40,
            "admin_api_token": "b" * 40,
            "cors_origins": "https://careers.example.org,http://localhost:15173",
            **overrides,
        },
    )


def test_production_supports_https_and_private_tunnel() -> None:
    assert production().app_env == "production"


@pytest.mark.parametrize(
    "overrides",
    [
        {"database_url": "sqlite:///local.db"},
        {"model_bundle_path": None},
        {"candidate_api_token": "CHANGE_ME"},
        {"admin_api_token": "a" * 40},
        {"cors_origins": "*"},
        {"cors_origins": "http://public.example.org"},
        {"cors_origins": "https://user:password@example.org"},
        {"cors_origins": "https://example.org/path"},
        {"cors_origins": ""},
        {"app_env": "prodution"},
    ],
)
def test_unsafe_production_config_is_rejected_without_leaking_tokens(overrides) -> None:
    with pytest.raises(ValidationError) as result:
        production(**overrides)
    assert "private@postgres" not in str(result.value)
    assert "a" * 40 not in str(result.value)


def test_candidate_api_responses_are_not_browser_cached(client) -> None:
    response = client.get("/api/profile", headers={"Authorization": "Bearer test-candidate-token"})
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert client.get("/api/profile").headers["Cache-Control"] == "no-store"
