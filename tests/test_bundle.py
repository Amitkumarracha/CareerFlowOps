import json
from pathlib import Path

import joblib
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

from apps.api.app.config import get_settings
from ingestion.runner import run_ingestion
from ml.inference.bundle import checksum, load_bundle
from pipelines.common import write
from pipelines.export_model import export_bundle

AUTH = {"Authorization": "Bearer test-candidate-token"}


@pytest.fixture
def bundle_path(tmp_path: Path) -> Path:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    weights = {
        "semantic": 0.4,
        "skill": 0.3,
        "eligibility": 0.15,
        "location": 0.08,
        "freshness": 0.07,
    }
    write(
        artifacts / "model.json",
        {"algorithm": "tfidf", "weights": weights, "model_version": "test-release"},
    )
    write(
        artifacts / "training.json",
        {
            "dataset_version": "test-only",
            "weights": weights,
            "runs": [{"algorithm": "tfidf", "run_id": "unit-test"}],
        },
    )
    write(
        artifacts / "evaluation.json",
        {
            "dataset_version": "test-only",
            "selected_algorithm": "tfidf",
            "labels_description": "unit test fixture",
            "results": [],
        },
    )
    write(
        artifacts / "registry.json",
        {
            "dataset_version": "test-only",
            "run_id": "unit-test",
            "model_name": "test",
            "version": "1",
            "alias": "production",
        },
    )
    vectorizer = TfidfVectorizer().fit(["Python software engineer", "Design research"])
    joblib.dump(vectorizer, artifacts / "tfidf.joblib")
    output = tmp_path / "release"
    export_bundle(artifacts, output)
    load_bundle.cache_clear()
    yield output
    load_bundle.cache_clear()


def test_bundle_predicts_with_fitted_vocabulary_and_saved_version(bundle_path) -> None:
    bundle = load_bundle(str(bundle_path))
    predictions = bundle.predict(
        {"skills": ["python"]}, [{"id": "one", "title": "Python software engineer"}]
    )
    assert predictions[0]["model_version"] == "test-release"
    assert predictions[0]["fallback_reason"] is None
    assert predictions[0]["explanation"]
    assert bundle.bundle_id == checksum(bundle_path / "manifest.json")


@pytest.mark.parametrize(
    "failure", ["corrupt", "missing", "extra", "symlink", "code", "metadata", "traversal"]
)
def test_bundle_fails_closed_before_deserializing(bundle_path, failure, monkeypatch) -> None:
    manifest_path = bundle_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if failure == "corrupt":
        (bundle_path / "tfidf.joblib").write_bytes(b"corrupt")
    elif failure == "missing":
        (bundle_path / "tfidf.joblib").unlink()
    elif failure == "extra":
        (bundle_path / "untracked.txt").write_text("unexpected")
    elif failure == "symlink":
        (bundle_path / "link").symlink_to(bundle_path / "model.json")
    elif failure == "code":
        manifest["code"]["ml/inference/ranker.py"] = "wrong-code"
    elif failure == "metadata":
        config = json.loads((bundle_path / "model.json").read_text())
        config["algorithm"] = "hybrid"
        write(bundle_path / "model.json", config)
        manifest["files"]["model.json"] = checksum(bundle_path / "model.json")
    else:
        manifest["files"]["../outside.joblib"] = "unexpected"
    write(manifest_path, manifest)
    monkeypatch.setattr(
        "ml.inference.bundle.joblib.load", lambda *_: pytest.fail("Invalid bundle was deserialized")
    )
    with pytest.raises(RuntimeError, match="failed validation"):
        load_bundle(str(bundle_path))


def test_production_readiness_and_recommendations_require_release(
    client, db, tmp_path, bundle_path, monkeypatch
) -> None:
    monkeypatch.setattr(get_settings(), "model_bundle_path", bundle_path)
    readiness = client.get("/ready")
    assert readiness.status_code == 200
    assert readiness.json()["model_version"] == "test-release"
    client.put("/api/profile", headers=AUTH, json={"skills": ["python"]})
    run_ingestion(db, tmp_path, fixture=True)
    predictions = client.get("/api/jobs/recommended?limit=2", headers=AUTH)
    assert predictions.status_code == 200
    assert all(
        row["model_version"] == "test-release" and row["fallback_reason"] is None
        for row in predictions.json()
    )
    assert client.get("/api/jobs/recommended?algorithm=hybrid", headers=AUTH).status_code == 422
    monkeypatch.setattr(get_settings(), "model_bundle_path", tmp_path / "absent")
    assert client.get("/ready").status_code == 503
    assert client.get("/api/jobs/recommended", headers=AUTH).status_code == 503


def test_export_preserves_previous_release_on_inconsistent_metadata(bundle_path) -> None:
    before = checksum(bundle_path / "manifest.json")
    artifacts = bundle_path.parent / "artifacts"
    write(artifacts / "registry.json", {"run_id": "wrong"})
    with pytest.raises((ValueError, KeyError)):
        export_bundle(artifacts, bundle_path)
    assert checksum(bundle_path / "manifest.json") == before
