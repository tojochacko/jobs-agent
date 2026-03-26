"""Dry-run script for the JobScout agent.

Usage (from inside the backend container or with uv):
    python -m backend.dry_run_scout

Prints LLM prompts, tool calls, and final scored jobs to stdout.
Requires ANTHROPIC_API_KEY (or OPENAI_API_KEY) and SERP_API_KEY in the environment.
"""
import json
import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-7s  %(name)s\n%(message)s\n",
    stream=sys.stdout,
)
# Quiet noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from backend.agents.job_scout import run_job_scout  # noqa: E402
from backend.database import SessionLocal  # noqa: E402
from backend.models import Preference  # noqa: E402
from backend.routers.preferences import _deserialize  # noqa: E402

FALLBACK_PREFERENCES = {
    "job_titles": ["Python Engineer", "Backend Engineer"],
    "location": "Remote",
    "remote_hybrid": "remote",
    "experience_level": "mid",
    "domain": "fintech",
    "company_size": [],
    "industry": [],
}


def _load_preferences() -> dict:
    db = SessionLocal()
    try:
        pref = db.query(Preference).first()
        if not pref:
            print("No preferences found in DB — using fallback.")
            return FALLBACK_PREFERENCES
        _deserialize(pref)
        return {
            "job_titles": pref.job_titles,
            "location": pref.location or "",
            "remote_hybrid": pref.remote_hybrid or "any",
            "experience_level": pref.experience_level or "",
            "domain": pref.domain or "",
            "company_size": pref.company_size,
            "industry": pref.industry,
        }
    finally:
        db.close()


if __name__ == "__main__":
    preferences = _load_preferences()

    print("=" * 60)
    print("DRY RUN — JobScout Agent")
    print("Preferences:", json.dumps(preferences, indent=2))
    print("=" * 60)

    jobs = run_job_scout(preferences)

    print("\n" + "=" * 60)
    print(f"RESULTS — {len(jobs)} job(s) above threshold")
    print("=" * 60)
    print(json.dumps(jobs, indent=2))
