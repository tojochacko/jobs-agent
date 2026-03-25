from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Job
from backend.scheduler import run_poll

router = APIRouter()


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    url: str
    description: Optional[str]
    location: Optional[str]
    match_score: Optional[float]
    source: str
    status: str
    error_reason: Optional[str]

    model_config = ConfigDict(from_attributes=True)


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).all()


# IMPORTANT: /jobs/refresh MUST be declared before /jobs/{job_id} to prevent
# FastAPI from matching the literal string "refresh" as a job_id parameter.
@router.post("/jobs/refresh")
def refresh_jobs():
    """Manually trigger a job discovery poll."""
    run_poll()
    return {"status": "poll triggered"}


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/jobs/{job_id}", response_model=JobResponse)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return job
