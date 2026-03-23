import json
import logging

import anthropic

from backend.config import settings
from backend.tools.serp import search_people

logger = logging.getLogger(__name__)

EXTRACT_SYSTEM = """You are an HR contact extractor. Given search results about a company's hiring team,
extract the most relevant recruiter or hiring manager's name and email.
Return ONLY a JSON object: {"hr_name": "...", "hr_email": "...", "hr_confidence": "search_result|inferred_pattern|unknown"}

If no email is found, infer a likely pattern (e.g. firstname.lastname@company.com) and set confidence to "inferred_pattern".
If you cannot determine any contact, set all fields to empty string and confidence to "unknown"."""


def find_hr_contact(company: str, job_title: str) -> dict:
    """
    Search SerpAPI for recruiter/hiring manager at the given company.
    Returns {"hr_name": str, "hr_email": str, "hr_confidence": str}
    """
    query = f'"{company}" recruiter hiring manager "{job_title}" site:linkedin.com OR email'
    try:
        results = search_people(query=query, num_results=5)
    except Exception as e:
        logger.warning(f"HR search failed: {e}")
        return {"hr_name": "", "hr_email": "", "hr_confidence": "unknown"}

    if not results:
        return {"hr_name": "", "hr_email": "", "hr_confidence": "unknown"}

    snippets = "\n".join(
        f"Title: {r.get('title', '')}\nURL: {r.get('link', '')}\nSnippet: {r.get('snippet', '')}"
        for r in results[:3]
    )

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=settings.OUTREACH_MODEL,
            max_tokens=256,
            system=EXTRACT_SYSTEM,
            messages=[{"role": "user", "content": f"Company: {company}\nJob: {job_title}\n\nSearch results:\n{snippets}"}],
        )
    except Exception as e:
        logger.warning(f"Claude extraction failed: {e}")
        return {"hr_name": "", "hr_email": "", "hr_confidence": "unknown"}

    for block in response.content:
        if getattr(block, "type", None) == "text":
            try:
                return json.loads(block.text)
            except json.JSONDecodeError:
                pass

    return {"hr_name": "", "hr_email": "", "hr_confidence": "unknown"}
