import json
import logging
import anthropic
from backend.config import settings
from backend.tools.playwright_tools import fetch_application_form
from backend.tools.resume_tools import tailor_resume

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an application form assistant. Given form fields and a tailored resume, produce a JSON object mapping each field name to its value from the resume. Use only information present in the resume. Return ONLY valid JSON with no markdown or commentary."""


def run_applicator(job_id: int, job_url: str, job_description: str, resume_path: str) -> dict:
    """
    Run the Applicator agent for a given job.

    Returns:
        {"status": "ready", "form_payload": {...}, "tailored_resume": "...", "form_fields": [...], "url": str}
        or {"status": "manual_required", "url": str}
    """
    # Step 1: Scrape the application form
    form_result = fetch_application_form(job_url)
    if form_result.get("status") == "manual_required":
        logger.info(f"Form scraping returned manual_required for job {job_id}: {job_url}")
        return {"status": "manual_required", "url": job_url}

    # Step 2: Tailor resume as text for form field population
    try:
        tailored = tailor_resume(
            job_description=job_description,
            master_resume_path=resume_path,
            output_format="text",
            model=settings.APPLICATOR_MODEL,
        )
    except Exception as e:
        logger.warning(f"Resume tailoring failed for job {job_id}: {e}")
        return {"status": "manual_required", "url": job_url}

    # Step 3: Use LLM to map resume data to form fields
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    try:
        response = client.messages.create(
            model=settings.APPLICATOR_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Form fields:\n{json.dumps(form_result['fields'], indent=2)}\n\n"
                        f"Tailored Resume:\n{tailored}\n\n"
                        "Return a JSON object mapping each field name to its value."
                    ),
                }
            ],
        )
    except Exception as e:
        logger.warning(f"LLM field mapping failed for job {job_id}: {e}")
        return {"status": "manual_required", "url": job_url}

    payload = {}
    for block in response.content:
        if getattr(block, "type", None) == "text":
            try:
                payload = json.loads(block.text)
            except json.JSONDecodeError:
                logger.warning(f"LLM returned non-JSON payload for job {job_id}: {block.text[:100]}")
                payload = {}
            break

    return {
        "status": "ready",
        "form_payload": payload,
        "tailored_resume": tailored,
        "form_fields": form_result.get("fields", []),
        "url": job_url,
    }
