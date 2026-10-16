from datetime import UTC, datetime

import pytest

from ml.evaluate.metrics import ranking_metrics
from ml.inference.ranker import load_weights, rank_jobs


def test_explained_hybrid_uses_configured_weights(monkeypatch) -> None:
    monkeypatch.setattr(
        "ml.inference.ranker.embedding_model",
        lambda *args: (_ for _ in ()).throw(OSError("unavailable")),
    )
    jobs = [
        {
            "id": "one",
            "title": "Python engineer",
            "description": "Python SQL Docker. 3+ years of experience",
            "location": "Pune",
            "remote": False,
            "posted_at": None,
            "skills": ["python", "sql", "docker"],
        }
    ]
    result = rank_jobs(
        {"skills": ["python", "sql"], "experience_years": 1, "location": "Pune"},
        jobs,
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
    )[0]
    assert result["matched_skills"] == ["python", "sql"]
    assert result["missing_skills"] == ["docker"]
    assert result["eligibility_score"] == 0
    assert result["location_score"] == 1
    assert result["freshness_score"] == 0.5
    assert result["fallback_reason"] and result["algorithm"] == "hybrid_tfidf"
    expected = sum(load_weights()[key] * result[f"{key}_score"] for key in load_weights())
    assert result["overall_score"] == pytest.approx(expected, abs=1e-6)


def test_empty_unknown_and_tfidf() -> None:
    assert rank_jobs({}, []) == []
    results = rank_jobs(
        {"skills": ["python"]},
        [
            {"id": "python", "title": "Python engineer", "description": "Python development"},
            {"id": "sales", "title": "Sales", "description": "Sell products"},
        ],
        algorithm="tfidf",
    )
    assert results[0]["job_id"] == "python"
    assert results[0]["eligibility_score"] == 0.5
    assert any("unknown" in text for text in results[0]["explanation"])
    assert rank_jobs({}, [{"id": "empty"}], algorithm="tfidf")[0]["overall_score"] == 0


def test_metrics_known_values_and_empty_relevance() -> None:
    metrics = ranking_metrics(["a", "b", "c", "d", "e"], {"a": 2, "c": 1})
    assert metrics["precision_at_5"] == 0.4 and metrics["recall_at_5"] == 1 and metrics["mrr"] == 1
    assert 0 < metrics["ndcg_at_5"] < 1
    assert ranking_metrics(["x"], {}) == dict.fromkeys(
        ["precision_at_5", "recall_at_5", "ndcg_at_5", "mrr"], 0
    )
    with pytest.raises(ValueError):
        ranking_metrics(["a", "a"], {"a": 1})


def test_invalid_weights_rejected(monkeypatch) -> None:
    monkeypatch.setenv("MATCH_SEMANTIC_WEIGHT", "-0.4")
    with pytest.raises(ValueError):
        load_weights()
