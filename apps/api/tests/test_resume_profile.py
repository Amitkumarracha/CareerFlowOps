import pymupdf
from sqlalchemy import select

from apps.api.app.models.entities import Candidate, Resume

AUTH = {"Authorization": "Bearer test-candidate-token"}


def pdf(text: str) -> bytes:
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((50, 50), text)
        return document.tobytes()


def test_upload_extract_review_and_delete(client, db) -> None:
    content = pdf(
        "Name: Test Candidate\ncandidate@example.org\nSkills\n"
        "Python, PostgreSQL, Docker\nEducation\nBSc Computer Science\n"
        "Projects\nFastAPI portfolio"
    )
    response = client.post(
        "/api/resumes",
        files={"file": ("../../resume.pdf", content, "application/pdf")},
        headers=AUTH,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "resume.pdf"
    assert body["extracted_profile"]["skills"] == ["docker", "fastapi", "python", "sql"]
    assert body["extracted_profile"]["experience_years"] is None
    assert "BSc" in body["extracted_profile"]["education"]
    assert client.get("/api/resumes/" + body["id"]).status_code == 401
    assert client.get("/api/resumes/" + body["id"], headers=AUTH).status_code == 200
    profile = client.get("/api/profile", headers=AUTH).json()
    profile["skills"] = ["Python", "PostgreSQL"]
    assert client.put("/api/profile", headers=AUTH, json=profile).json()["skills"] == [
        "python",
        "sql",
    ]
    assert client.delete("/api/profile", headers=AUTH).status_code == 204
    assert db.scalar(select(Resume)) is None
    assert db.scalar(select(Candidate)) is None


def test_invalid_uploads_and_validation(client, monkeypatch) -> None:
    from apps.api.app.config import get_settings

    assert (
        client.post(
            "/api/resumes", headers=AUTH, files={"file": ("x.pdf", b"not a PDF")}
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/api/resumes", headers=AUTH, files={"file": ("x.pdf", b"%PDF-broken")}
        ).status_code
        == 422
    )
    assert (
        client.post("/api/resumes", headers=AUTH, files={"file": ("x.pdf", pdf(""))}).status_code
        == 422
    )
    monkeypatch.setattr(get_settings(), "max_resume_bytes", 10)
    assert (
        client.post(
            "/api/resumes", headers=AUTH, files={"file": ("x.pdf", b"%PDF-" + b"x" * 20)}
        ).status_code
        == 413
    )
    assert (
        client.put("/api/profile", headers=AUTH, json={"experience_years": -1}).status_code == 422
    )
    assert client.get("/api/profile", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_candidate_cannot_read_another_resume(client, db) -> None:
    db.add(Candidate(id="other"))
    db.flush()
    resume = Resume(
        candidate_id="other", filename="private.pdf", extracted_text="private", extracted_profile={}
    )
    db.add(resume)
    db.commit()
    assert client.get("/api/resumes/" + resume.id, headers=AUTH).status_code == 404
