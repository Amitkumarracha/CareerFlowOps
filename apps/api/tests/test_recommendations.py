from ingestion.runner import run_ingestion

AUTH = {"Authorization": "Bearer test-candidate-token"}


def test_recommendations_explain_and_validate(client, db, tmp_path) -> None:
    assert client.get("/api/jobs/recommended").status_code == 401
    assert client.get("/api/jobs/recommended", headers=AUTH).status_code == 422
    client.put(
        "/api/profile",
        headers=AUTH,
        json={"skills": ["python", "sql"], "summary": "Backend engineer"},
    )
    run_ingestion(db, tmp_path, fixture=True)
    response = client.get("/api/jobs/recommended?algorithm=tfidf&limit=3", headers=AUTH)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 3
    assert results[0]["overall_score"] >= results[1]["overall_score"]
    for row in results:
        assert row["explanation"] and row["job"]["apply_url"].startswith("https://")
        assert 0 <= row["semantic_score"] <= 1
        assert row["algorithm"] == "tfidf"
    assert client.get("/api/jobs/recommended?min_score=2", headers=AUTH).status_code == 422


def test_registry_failure_is_explained(client, db, tmp_path, monkeypatch) -> None:
    from apps.api.app.config import get_settings

    monkeypatch.setattr(get_settings(), "use_model_registry", True)

    def unavailable(*args):
        raise ConnectionError("offline")

    monkeypatch.setattr("apps.api.app.routes.recommendations.predict_registered", unavailable)
    monkeypatch.setattr("ml.inference.ranker.embedding_model", unavailable)
    # Model failure class recognized by the local fallback.
    monkeypatch.setattr(
        "ml.inference.ranker.embedding_model",
        lambda *args: (_ for _ in ()).throw(OSError("offline")),
    )
    client.put("/api/profile", headers=AUTH, json={"skills": ["python"]})
    run_ingestion(db, tmp_path, fixture=True)
    result = client.get("/api/jobs/recommended", headers=AUTH).json()
    assert "registry unavailable" in result[0]["fallback_reason"]
    assert result[0]["algorithm"] == "hybrid_tfidf"
