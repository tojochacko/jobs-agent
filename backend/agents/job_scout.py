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
[{"title": "...", "company": "...", "location": "...", "url": "...", "match_score": 0.85}]"""


def run_job_scout(preferences: dict) -> list[dict]:
    """Fetch jobs from SerpAPI for each job title, then score all results via LLM.
    Returns jobs scoring >= JOB_MATCH_THRESHOLD.
    """
    location = preferences.get("location", "")
    remote_hybrid = preferences.get("remote_hybrid", "any")
    all_jobs: list[dict] = []
    for title in preferences.get("job_titles", []):
        results = search_jobs(query=title, location=location, remote_hybrid=remote_hybrid)
        all_jobs.extend(results)

    if not all_jobs:
        return []

    # Strip description — reduces prompt size; LLM scores on title/company/location only
    slim_jobs = [
        {k: v for k, v in j.items() if k != "description"}
        for j in all_jobs
    ]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Preferences:\n{json.dumps(preferences, indent=2)}\n\n"
                f"Job listings to score:\n{json.dumps(slim_jobs, indent=2)}\n\n"
                "Return a JSON array of all listings with a match_score field added to each."
            ),
        },
    ]

    response = llm.complete(
        model=settings.SCOUT_MODEL,
        max_tokens=8192,
        messages=messages,
    )

    if response.content:
        try:
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            scored = json.loads(raw)
            # Merge scores back using (title, company) key — url is often empty
            score_by_key = {
                (j.get("title"), j.get("company")): j.get("match_score", 0)
                for j in scored
            }
            result = []
            for job in all_jobs:
                key = (job.get("title"), job.get("company"))
                score = score_by_key.get(key, 0)
                if score >= settings.JOB_MATCH_THRESHOLD:
                    result.append({**job, "match_score": score})
            return result
        except (json.JSONDecodeError, TypeError):
            return []
    return []
