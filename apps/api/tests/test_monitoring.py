from apps.api.app.config import get_settings


def test_metrics_have_bounded_route_labels_and_upload_limit(client) -> None:
    client.get("/api/jobs/nonexistent-one")
    client.get("/api/jobs/nonexistent-two")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "careerflowops_http_requests_total" in response.text
    assert 'route="/api/jobs/{job_id}"' in response.text
    assert "nonexistent-one" not in response.text
    too_large = client.post("/api/resumes", content=b"", headers={"Content-Length": "999999999"})
    assert too_large.status_code == 413


def test_metrics_can_be_disabled(client, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "prometheus_enabled", False)
    assert client.get("/metrics").status_code == 404
