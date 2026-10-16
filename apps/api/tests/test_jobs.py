from ingestion.runner import run_ingestion


def test_search_validation_and_provenance(client, db, tmp_path) -> None:
    run_ingestion(db, tmp_path, fixture=True)
    response = client.get("/api/jobs?limit=3")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 29
    assert len(body["items"]) == 3
    job = body["items"][0]
    assert client.get("/api/jobs/" + job["id"]).json()["sources"][0]["source_payload_hash"]
    assert all(
        j["company"] == "linear" for j in client.get("/api/jobs?source=ashby").json()["items"]
    )
    assert client.get("/api/jobs?keyword=%25").json()["total"] == 0
    assert client.get("/api/jobs?limit=1001").status_code == 422
    assert client.get("/api/jobs/not-found").status_code == 404
    assert client.get("/api/jobs?remote=invalid").status_code == 422
