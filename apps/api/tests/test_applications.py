from sqlalchemy import select

from apps.api.app.models.entities import Application, Candidate
from ingestion.runner import run_ingestion

AUTH = {"Authorization": "Bearer test-candidate-token"}


def test_save_and_application_history_are_idempotent(client, db, tmp_path) -> None:
    run_ingestion(db, tmp_path, fixture=True)
    job_id = client.get("/api/jobs?limit=1").json()["items"][0]["id"]
    for _ in range(2):
        assert client.post("/api/saved", headers=AUTH, json={"job_id": job_id}).status_code == 200
    assert len(client.get("/api/saved", headers=AUTH).json()) == 1
    apps = client.get("/api/applications", headers=AUTH).json()
    assert len(apps) == 1 and len(apps[0]["history"]) == 1
    application_id = apps[0]["id"]
    for _ in range(2):
        response = client.patch(
            "/api/applications/" + application_id,
            headers=AUTH,
            json={"status": "APPLIED", "notes": "Applied manually on official site"},
        )
        assert response.status_code == 200
    assert len(response.json()["history"]) == 2
    assert (
        client.patch(
            "/api/applications/" + application_id, headers=AUTH, json={"status": "SPAM"}
        ).status_code
        == 422
    )
    assert client.delete("/api/saved/" + job_id, headers=AUTH).status_code == 204
    assert len(client.get("/api/applications", headers=AUTH).json()) == 1


def test_other_candidate_application_is_private(client, db, tmp_path) -> None:
    run_ingestion(db, tmp_path, fixture=True)
    job_id = client.get("/api/jobs?limit=1").json()["items"][0]["id"]
    db.add(Candidate(id="other"))
    db.flush()
    application = Application(candidate_id="other", job_id=job_id, status="SAVED", notes="private")
    db.add(application)
    db.commit()
    assert (
        client.patch(
            "/api/applications/" + application.id, headers=AUTH, json={"status": "OFFER"}
        ).status_code
        == 404
    )
    assert client.get("/api/applications", headers=AUTH).json() == []
    assert db.scalars(select(Application)).one().notes == "private"
