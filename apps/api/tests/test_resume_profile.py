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
    assert client.get("/api/resumes").status_code == 401
    summaries = client.get("/api/resumes", headers=AUTH).json()
    assert summaries == [
        {"id": body["id"], "filename": "resume.pdf", "created_at": body["created_at"]}
    ]
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
    assert client.get("/api/resumes", headers=AUTH).json() == []
    assert client.delete("/api/resumes/" + resume.id, headers=AUTH).status_code == 404


def test_delete_extraction_preserves_edited_profile(client) -> None:
    body = client.post(
        "/api/resumes",
        files={"file": ("resume.pdf", pdf("Skills\nPython software engineer"))},
        headers=AUTH,
    ).json()
    client.put("/api/profile", headers=AUTH, json={"summary": "My edited summary"})
    assert client.delete("/api/resumes/" + body["id"], headers=AUTH).status_code == 204
    assert client.get("/api/resumes", headers=AUTH).json() == []
    assert client.get("/api/profile", headers=AUTH).json()["summary"] == "My edited summary"


def test_encrypted_and_excessive_page_pdfs_are_rejected(client) -> None:
    with pymupdf.open() as document:
        document.new_page()
        encrypted = document.tobytes(
            encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="test-only", owner_pw="test-only"
        )
    assert (
        client.post("/api/resumes", headers=AUTH, files={"file": ("x.pdf", encrypted)}).status_code
        == 422
    )
    with pymupdf.open() as document:
        for _ in range(31):
            document.new_page()
        many_pages = document.tobytes()
    assert (
        client.post("/api/resumes", headers=AUTH, files={"file": ("x.pdf", many_pages)}).status_code
        == 422
    )
