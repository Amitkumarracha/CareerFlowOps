import re

import pymupdf
from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy.orm import Session

from apps.api.app.models.entities import CandidateProfile, CandidateSkill
from apps.api.app.schemas.profile import ProfileData
from ml.features.skills import extract_skills

HEADINGS = {
    "education": "education",
    "academic background": "education",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "projects": "projects",
    "certifications": "certifications",
    "certificates": "certifications",
    "summary": "summary",
    "professional summary": "summary",
    "skills": "skills",
    "technical skills": "skills",
}


def parse_text(text: str) -> ProfileData:
    sections: dict[str, list[str]] = {}
    section: str | None = None
    for line in text.splitlines():
        heading = line.strip().rstrip(":").casefold()
        if heading in HEADINGS:
            section = HEADINGS[heading]
        elif section:
            sections.setdefault(section, []).append(line)
    email = re.search(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    phone = re.search(
        r"(?<!\w)(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\w)", text
    )
    name = re.search(r"^\s*Name:\s*([^\n]{2,100})", text, re.M | re.I)
    return ProfileData(
        name=name.group(1).strip() if name else None,
        email=email.group(0) if email else None,
        phone=phone.group(0).strip() if phone else None,
        skills=extract_skills(text),
        **{
            key: "\n".join(sections.get(key, [])).strip()[:10000]
            for key in ["education", "experience", "projects", "certifications", "summary"]
        },
    )


def extract_pdf(content: bytes) -> tuple[str, ProfileData]:
    if not content.startswith(b"%PDF-"):
        raise HTTPException(415, "Upload a valid PDF file")
    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if document.needs_pass:
                raise HTTPException(422, "Password-protected PDFs are not supported")
            if document.page_count > 30:
                raise HTTPException(422, "Resume must have at most 30 pages")
            parts: list[str] = []
            length = 0
            for page in document:
                part = page.get_text()
                length += len(part)
                if length > 200000:
                    raise HTTPException(422, "Extracted text is too large")
                parts.append(part)
            text = "\n".join(parts).strip()
    except (pymupdf.FileDataError, pymupdf.EmptyFileError, RuntimeError, ValueError) as exc:
        raise HTTPException(
            422, "PDF could not be read; upload an unencrypted text-based PDF"
        ) from exc
    if len(text) < 20:
        raise HTTPException(
            422, "No readable resume text found. Export a PDF with selectable text."
        )
    return text, parse_text(text)


def store_profile(db: Session, candidate_id: str, data: ProfileData) -> CandidateProfile:
    profile = db.get(CandidateProfile, candidate_id)
    if profile is None:
        profile = CandidateProfile(candidate_id=candidate_id)
        db.add(profile)
    for key, value in data.model_dump().items():
        setattr(profile, key, value)
    db.execute(delete(CandidateSkill).where(CandidateSkill.candidate_id == candidate_id))
    db.add_all([CandidateSkill(candidate_id=candidate_id, skill=skill) for skill in data.skills])
    db.flush()
    return profile
