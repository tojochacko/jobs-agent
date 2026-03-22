import json
import anthropic
from backend.config import settings
from backend.tools.serp import search_jobs

TOOLS = [
    {
        "name": "search_jobs",
        "description": "Search for job listings using SerpAPI Google Jobs. Call once per job title.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Job title + keywords, e.g. 'Senior Python Engineer remote'"
                },
                "location": {
                    "type": "string",
                    "description": "Location filter, e.g. 'Remote' or 'New York, NY'"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to fetch (max 20)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    }
]

SYSTEM_PROMPT = """You are a job search assistant.
1. Use search_jobs to find jobs for each job title in the user's preferences.
2. Score each result 0.0–1.0 based on how well it matches the criteria.
3. Return ONLY a valid JSON array. No other text.

Scoring weights: title match (high), remote/location match (high), experience level (medium), domain (medium), company size (low).

Output format:
[{"title": "...", "company": "...", "location": "...", "description": "...", "url": "...", "match_score": 0.85}]"""


def _execute_tool(name: str, tool_input: dict) -> str:
    if name == "search_jobs":
        results = search_jobs(
            query=tool_input["query"],
            location=tool_input.get("location", ""),
            num_results=tool_input.get("num_results", 10),
        )
        return json.dumps(results)
    raise ValueError(f"Unknown tool: {name}")


def run_job_scout(preferences: dict) -> list[dict]:
    """Run the JobScout agentic loop. Returns jobs scoring >= JOB_MATCH_THRESHOLD."""
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    messages = [
        {
            "role": "user",
            "content": f"Find and score jobs for these preferences:\n{json.dumps(preferences, indent=2)}\n\nSearch each job title. Return a JSON array of scored jobs.",
        }
    ]

    while True:
        response = client.messages.create(
            model=settings.SCOUT_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    try:
                        jobs = json.loads(block.text)
                        return [j for j in jobs if j.get("match_score", 0) >= settings.JOB_MATCH_THRESHOLD]
                    except (json.JSONDecodeError, TypeError):
                        return []
            return []

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if getattr(block, "type", None) == "tool_use":
                    result = _execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            continue

        # Unexpected stop reason (max_tokens, stop_sequence, etc.) — abort gracefully
        return []
