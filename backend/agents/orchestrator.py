import json
import logging
import litellm
from backend.config import settings

logger = logging.getLogger(__name__)

SCORE_SYSTEM = """You are a job relevance scorer. Given a job posting and user preferences, return ONLY a single decimal number between 0.0 and 1.0 representing how well the job matches the preferences.

Scoring weights:
- Job title match: 35%
- Remote/location match: 30%
- Experience level match: 20%
- Domain/tech stack match: 10%
- Company size match: 5%

Return ONLY the number. Example: 0.87"""


def score_job(job_data: dict, preferences: dict) -> float:
    """
    Score a single job against user preferences.
    Returns a float 0.0–1.0. Returns 0.0 on any error.
    """
    prompt = (
        f"User Preferences:\n{json.dumps(preferences, indent=2)}\n\n"
        f"Job Posting:\nTitle: {job_data.get('title', '')}\n"
        f"Company: {job_data.get('company', '')}\n"
        f"Location: {job_data.get('location', '')}\n"
        f"Description: {job_data.get('description', '')[:500]}\n\n"
        f"Score this job (0.0–1.0):"
    )
    try:
        response = litellm.completion(
            model=settings.ORCHESTRATOR_MODEL,
            max_tokens=16,
            messages=[
                {"role": "system", "content": SCORE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        raw = response.choices[0].message.content.strip()
        score = float(raw)
        return max(0.0, min(1.0, score))
    except Exception as e:
        logger.warning("score_job failed: %s", e)
    return 0.0
