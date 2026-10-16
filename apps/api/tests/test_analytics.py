from ingestion.runner import run_ingestion

ADMIN = {"Authorization": "Bearer test-admin-token"}
CANDIDATE = {"Authorization": "Bearer test-candidate-token"}


def test_aggregate_metrics_are_real_and_private(client, db, tmp_path) -> None:
    assert client.get("/api/tpo", headers=CANDIDATE).status_code == 401
    empty = client.get("/api/tpo", headers=ADMIN).json()
    assert empty["active_students"] == empty["applications"] == empty["active_opportunities"] == 0
    run_ingestion(db, tmp_path, fixture=True)
    client.put(
        "/api/profile",
        headers=CANDIDATE,
        json={"name": "Private name", "email": "private@example.org", "skills": ["python", "sql"]},
    )
    job = client.get("/api/jobs?limit=1").json()["items"][0]
    application = client.post(
        "/api/applications", headers=CANDIDATE, json={"job_id": job["id"], "status": "OFFER"}
    ).json()
    assert application["status"] == "OFFER"
    response = client.get("/api/tpo", headers=ADMIN)
    data = response.json()
    assert data["active_students"] == data["applications"] == data["offers"] == 1
    assert data["active_opportunities"] == 29
    assert "private@example.org" not in response.text and "Private name" not in response.text
