from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from apps.api.app.config import get_settings
from apps.api.app.db import Base, get_db
from apps.api.app.main import app
from apps.api.app.models import entities  # noqa: F401


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db: Session, monkeypatch, tmp_path) -> Generator[TestClient, None, None]:
    settings = get_settings()
    monkeypatch.setattr(settings, "candidate_api_token", "test-candidate-token")
    monkeypatch.setattr(settings, "admin_api_token", "test-admin-token")
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as instance:
        yield instance
    app.dependency_overrides.clear()
