import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Job, Application, Resume
from backend.agents.applicator import run_applicator

router = APIRouter()


def get_resume_path(db: Session) -> str | None:
    resume = db.query(Resume).first()
    return resume.filepath if resume else None


class TriggerApplicationRequest(BaseModel):
    job_id: int


class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    tailored_resume_path: Optional[str] = None
    tailored_resume_text: Optional[str] = None
    form_payload: Optional[str] = None
    status: str
    notes: Optional[str] = None
    applied_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PatchApplicationRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


@router.post("/applications", response_model=ApplicationResponse)
def trigger_application(body: TriggerApplicationRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == body.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in ("applying", "applied"):
        raise HTTPException(status_code=409, detail=f"Job is already in status: {job.status}")

    job.status = "applying"
    db.commit()

    resume_path = get_resume_path(db)
    result = run_applicator(
        job_id=job.id,
        job_url=job.url,
        job_description=job.description or "",
        resume_path=resume_path or "",
    )

    status = "manual_required" if result["status"] == "manual_required" else "pending"
    app = Application(
        job_id=job.id,
        tailored_resume_text=result.get("tailored_resume", ""),
        form_payload=json.dumps(result.get("form_payload", {})),
        status=status,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.post("/applications/{app_id}/open")
def open_in_browser(app_id: int, db: Session = Depends(get_db)):
    """Launch Playwright with the pre-filled form for supervised submission."""
    from backend.tools.playwright_tools import open_prefilled_form
    import threading
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    job = db.query(Job).filter(Job.id == app.job_id).first()
    payload = json.loads(app.form_payload or "{}")
    threading.Thread(target=open_prefilled_form, args=(job.url, payload), daemon=True).start()
    return {"status": "browser_opened", "url": job.url}


@router.get("/applications", response_model=list[ApplicationResponse])
def list_applications(db: Session = Depends(get_db)):
    return db.query(Application).all()


@router.patch("/applications/{app_id}", response_model=ApplicationResponse)
def update_application(app_id: int, body: PatchApplicationRequest, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if body.status:
        app.status = body.status
        if body.status == "submitted":
            app.applied_at = datetime.utcnow()
            job = db.query(Job).filter(Job.id == app.job_id).first()
            if job:
                job.status = "applied"
    if body.notes is not None:
        app.notes = body.notes

    db.commit()
    db.refresh(app)
    return app
