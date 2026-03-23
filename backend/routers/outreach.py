from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Job, Outreach, Resume
from backend.agents.outreach import run_outreach
from backend.tools.email_tools import send_email
from backend.config import settings

router = APIRouter()


def get_resume_path(db: Session) -> str | None:
    resume = db.query(Resume).first()
    return resume.filepath if resume else None


class TriggerOutreachRequest(BaseModel):
    job_id: int


class OutreachResponse(BaseModel):
    id: int
    job_id: int
    hr_name: Optional[str] = None
    hr_email: Optional[str] = None
    hr_confidence: Optional[str] = None
    cover_letter: Optional[str] = None
    resume_version_path: Optional[str] = None
    status: str
    sent_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PatchOutreachRequest(BaseModel):
    hr_name: Optional[str] = None
    hr_email: Optional[str] = None
    cover_letter: Optional[str] = None
    # Note: status is intentionally excluded — only /send can set status=sent


@router.post("/outreach", response_model=OutreachResponse)
def trigger_outreach(body: TriggerOutreachRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == body.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in ("emailing", "emailed"):
        raise HTTPException(status_code=409, detail=f"Job is already in status: {job.status}")

    job.status = "emailing"
    db.commit()

    resume_path = get_resume_path(db)
    try:
        result = run_outreach(
            job_id=job.id,
            company=job.company,
            job_description=job.description or "",
            resume_path=resume_path or "",
            output_dir=settings.UPLOAD_DIR,
        )
    except Exception as e:
        job.status = "error"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    record = Outreach(
        job_id=job.id,
        hr_name=result["hr_name"],
        hr_email=result["hr_email"],
        hr_confidence=result["hr_confidence"],
        cover_letter=result["cover_letter"],
        resume_version_path=result["resume_version_path"],
        status="draft",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/outreach", response_model=list[OutreachResponse])
def list_outreach(db: Session = Depends(get_db)):
    return db.query(Outreach).all()


@router.patch("/outreach/{outreach_id}", response_model=OutreachResponse)
def update_outreach(outreach_id: int, body: PatchOutreachRequest, db: Session = Depends(get_db)):
    record = db.query(Outreach).filter(Outreach.id == outreach_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Outreach record not found")
    if body.hr_name is not None:
        record.hr_name = body.hr_name
    if body.hr_email is not None:
        record.hr_email = body.hr_email
    if body.cover_letter is not None:
        record.cover_letter = body.cover_letter
    db.commit()
    db.refresh(record)
    return record


@router.post("/outreach/{outreach_id}/send", response_model=OutreachResponse)
def send_outreach(outreach_id: int, db: Session = Depends(get_db)):
    record = db.query(Outreach).filter(Outreach.id == outreach_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Outreach record not found")
    if not record.hr_email:
        raise HTTPException(status_code=400, detail="HR email address is required before sending")
    if record.status == "sent":
        raise HTTPException(status_code=409, detail="Already sent")

    job = db.query(Job).filter(Job.id == record.job_id).first()
    subject = f"Application for {job.title}" if job else "Job Application"
    send_email(
        to=record.hr_email,
        subject=subject,
        body=record.cover_letter or "",
        attachment_path=record.resume_version_path or "",
        db=db,
    )

    record.status = "sent"
    record.sent_at = datetime.utcnow()
    if job:
        job.status = "emailed"
    db.commit()
    db.refresh(record)
    return record
