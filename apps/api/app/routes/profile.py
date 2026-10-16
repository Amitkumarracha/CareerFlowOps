from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from apps.api.app.config import get_settings
from apps.api.app.db import get_db
from apps.api.app.dependencies.auth import candidate
from apps.api.app.models.entities import (
    Application,
    ApplicationHistory,
    Candidate,
    CandidateProfile,
    CandidateSkill,
    Resume,
    SavedJob,
)
from apps.api.app.schemas.profile import ProfileData, ResumeOut
from apps.api.app.services.resumes import extract_pdf, store_profile

router = APIRouter(prefix="/api", tags=["candidate"])


@router.get("/profile", response_model=ProfileData)
def get_profile(
    candidate_id: str = Depends(candidate), db: Session = Depends(get_db)
) -> ProfileData:
    profile = db.get(CandidateProfile, candidate_id)
    return ProfileData.model_validate(profile) if profile else ProfileData()


@router.put("/profile", response_model=ProfileData)
def update_profile(
    data: ProfileData, candidate_id: str = Depends(candidate), db: Session = Depends(get_db)
) -> CandidateProfile:
    profile = store_profile(db, candidate_id, data)
    db.commit()
    return profile


@router.post("/resumes", response_model=ResumeOut, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    candidate_id: str = Depends(candidate),
    db: Session = Depends(get_db),
) -> Resume:
    try:
        content = await file.read(get_settings().max_resume_bytes + 1)
    finally:
        await file.close()
    if len(content) > get_settings().max_resume_bytes:
        raise HTTPException(413, "Resume exceeds the 5 MB upload limit")
    text, profile = extract_pdf(content)
    filename = PurePosixPath((file.filename or "resume.pdf").replace("\\", "/")).name[:250]
    resume = Resume(
        candidate_id=candidate_id,
        filename=filename,
        extracted_text=text,
        extracted_profile=profile.model_dump(),
    )
    db.add(resume)
    store_profile(db, candidate_id, profile)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("/resumes/{resume_id}", response_model=ResumeOut)
def get_resume(
    resume_id: str, candidate_id: str = Depends(candidate), db: Session = Depends(get_db)
) -> Resume:
    resume = db.scalar(
        select(Resume).where(Resume.id == resume_id, Resume.candidate_id == candidate_id)
    )
    if resume is None:
        raise HTTPException(404, "Resume not found")
    return resume


@router.delete("/resumes/{resume_id}", status_code=204)
def delete_resume(
    resume_id: str, candidate_id: str = Depends(candidate), db: Session = Depends(get_db)
) -> Response:
    resume = get_resume(resume_id, candidate_id, db)
    db.delete(resume)
    db.commit()
    return Response(status_code=204)


@router.delete("/profile", status_code=204)
def delete_candidate_data(
    candidate_id: str = Depends(candidate), db: Session = Depends(get_db)
) -> Response:
    application_ids = select(Application.id).where(Application.candidate_id == candidate_id)
    db.execute(
        delete(ApplicationHistory).where(ApplicationHistory.application_id.in_(application_ids))
    )
    for entity in [Application, SavedJob, Resume, CandidateSkill, CandidateProfile]:
        db.execute(delete(entity).where(entity.candidate_id == candidate_id))
    db.execute(delete(Candidate).where(Candidate.id == candidate_id))
    db.commit()
    return Response(status_code=204)
