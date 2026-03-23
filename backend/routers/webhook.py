import logging
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import Optional
from backend.config import settings
from backend.database import get_db
from backend.models import Job
from backend.agents.orchestrator import score_job
from backend.scheduler import get_preferences_dict

logger = logging.getLogger(__name__)
router = APIRouter()


class WebhookJob(BaseModel):
    title: str
    company: str
    url: str
    description: str = ""
    location: str = ""


class WebhookPayload(BaseModel):
    source: str
    jobs: list[WebhookJob]


@router.post("/webhook/job-alerts")
def receive_job_alerts(
    payload: WebhookPayload,
    x_webhook_secret: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    # Validate secret
    if not x_webhook_secret or x_webhook_secret != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Webhook-Secret header")

    preferences = get_preferences_dict()
    inserted = 0
    skipped_score = 0
    skipped_duplicate = 0

    for job_data in payload.jobs:
        job_dict = job_data.model_dump()

        # Score against preferences (skip scoring if no preferences and bypass is off)
        if preferences and not settings.WEBHOOK_BYPASS_THRESHOLD:
            match_score = score_job(job_dict, preferences)
            if match_score < settings.JOB_MATCH_THRESHOLD:
                skipped_score += 1
                continue
        elif not preferences and not settings.WEBHOOK_BYPASS_THRESHOLD:
            skipped_score += 1
            continue
        else:
            # bypass_threshold=True or no preferences with bypass — store with score 0 if no prefs
            match_score = score_job(job_dict, preferences) if preferences else 0.0

        job = Job(
            title=job_dict["title"],
            company=job_dict["company"],
            url=job_dict["url"],
            description=job_dict.get("description", ""),
            location=job_dict.get("location", ""),
            match_score=match_score,
            source="webhook",
            status="new",
        )
        db.add(job)
        try:
            db.commit()
            inserted += 1
        except IntegrityError:
            db.rollback()
            skipped_duplicate += 1

    logger.info(
        f"Webhook from '{payload.source}': {inserted} inserted, "
        f"{skipped_score} below threshold, {skipped_duplicate} duplicates"
    )
    return {
        "status": "ok",
        "inserted": inserted,
        "skipped_score": skipped_score,
        "skipped_duplicate": skipped_duplicate,
    }
