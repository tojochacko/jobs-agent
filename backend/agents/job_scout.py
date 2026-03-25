import json
from backend import llm
from backend.config import settings
from backend.tools.serp import search_jobs

SYSTEM_PROMPT = """You are a job relevance scorer.

You will be given a list of job listings and the user's job search preferences.
Score each listing 0.0–1.0 based on how well it matches the preferences.
Return ONLY a valid JSON array — no other text, no explanation.

Scoring weights:
- Title match (high): does the job title align with what the user is looking for?
- Remote/location (high): does the location match the preference?
- Experience level (medium): does the seniority fit?
- Domain (medium): does the company domain match?
- Company size (low): does company size fit the preference?

Output format:
[{"title": "...", "company": "...", "location": "...", "description": "...", "url": "...", "match_score": 0.85}]"""


def run_job_scout(preferences: dict) -> list[dict]:
    """Fetch jobs from SerpAPI for each job title, then score all results via LLM.
    Returns jobs scoring >= JOB_MATCH_THRESHOLD.
    """
    location = preferences.get("location", "")
    all_jobs: list[dict] = []
    for title in preferences.get("job_titles", []):
        results = search_jobs(query=title, location=location)
        all_jobs.extend(results)

    if not all_jobs:
        return []

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Preferences:\n{json.dumps(preferences, indent=2)}\n\n"
                f"Job listings to score:\n{json.dumps(all_jobs, indent=2)}\n\n"
                "Return a JSON array of all listings with a match_score field added to each."
            ),
        },
    ]

    response = llm.complete(
        model=settings.SCOUT_MODEL,
        max_tokens=4096,
        messages=messages,
    )

    if response.content:
        try:
            jobs = json.loads(response.content)
            return [j for j in jobs if j.get("match_score", 0) >= settings.JOB_MATCH_THRESHOLD]
        except (json.JSONDecodeError, TypeError):
            return []
    return []
