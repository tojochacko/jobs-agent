import json
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.exc import IntegrityError
from backend.database import SessionLocal
from backend.models import Preference, Job
from backend.agents.job_scout import run_job_scout

logger = logging.getLogger(__name__)


def get_preferences_dict() -> dict | None:
    db = SessionLocal()
    try:
        pref = db.query(Preference).first()
        if not pref:
            return None
        return {
            "job_titles": json.loads(pref.job_titles),
            "location": pref.location or "",
            "remote_hybrid": pref.remote_hybrid or "any",
            "experience_level": pref.experience_level or "",
            "domain": pref.domain or "",
            "company_size": json.loads(pref.company_size or "[]"),
        }
    finally:
        db.close()


def run_poll():
    """One job discovery poll. Called on startup and by scheduler."""
    preferences = get_preferences_dict()
    if not preferences:
        logger.info("No preferences configured — skipping job poll")
        return

    logger.info("Running job scout poll...")
    try:
        jobs = run_job_scout(preferences)
    except Exception as e:
        logger.error(f"Job scout failed: {e}")
        return

    db = SessionLocal()
    try:
        inserted = 0
        for job_data in jobs:
            job = Job(
                title=job_data["title"],
                company=job_data["company"],
                url=job_data["url"],
                description=job_data.get("description", ""),
                location=job_data.get("location", ""),
                match_score=job_data.get("match_score", 0.0),
                source="serpapi",
                status="new",
            )
            db.add(job)
            try:
                db.commit()
                inserted += 1
            except IntegrityError:
                db.rollback()  # duplicate URL — skip silently
        logger.info(f"Poll complete: {inserted} new jobs")
    finally:
        db.close()


def start_scheduler(poll_interval_hrs: int = 6):
    """Start background scheduler and run an immediate poll on startup."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_poll, "interval", hours=poll_interval_hrs)
    scheduler.start()
    run_poll()  # immediate poll on startup — no waiting for first interval
    return scheduler
