# backend/tests/test_job_scout_agent.py
import json
import pytest
from unittest.mock import patch, call
from backend.llm import LLMResponse
from backend.agents.job_scout import run_job_scout

PREFERENCES = {
    "job_titles": ["Python Engineer"],
    "location": "Remote",
    "remote_hybrid": "remote",
    "experience_level": "senior",
    "domains": ["fintech"],
    "company_size": ["startup"],
}

MOCK_SERP_RESULTS = [
    {
        "title": "Senior Python Engineer",
        "company": "Acme",
        "location": "Remote",
        "description": "Build APIs",
        "url": "https://acme.com/jobs/1",
    }
]


def _score_response(scored_jobs: list[dict]) -> LLMResponse:
    return LLMResponse(content=json.dumps(scored_jobs), tool_calls=[])


def test_run_job_scout_fetches_serp_once_per_job_title():
    """search_jobs is called directly by the agent — once per job title, no LLM tool call."""
    preferences = {**PREFERENCES, "job_titles": ["Python Engineer", "Backend Engineer"]}
    scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.9}]
    with patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS) as mock_serp, \
         patch("backend.agents.job_scout.llm.complete", return_value=_score_response(scored)):
        run_job_scout(preferences)
    assert mock_serp.call_count == 2
    calls = [c.kwargs["query"] for c in mock_serp.call_args_list]
    assert "Python Engineer" in calls[0]
    assert "Backend Engineer" in calls[1]


def test_run_job_scout_calls_llm_exactly_once_with_no_tools():
    """LLM is called once for scoring only — no agentic loop, no tools passed."""
    scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.9}]
    with patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS), \
         patch("backend.agents.job_scout.llm.complete", return_value=_score_response(scored)) as mock_llm:
        run_job_scout(PREFERENCES)
    assert mock_llm.call_count == 1
    _, kwargs = mock_llm.call_args
    assert kwargs.get("tools") is None


def test_run_job_scout_passes_serp_results_to_llm():
    """Fetched job results are included in the messages sent to the LLM for scoring."""
    scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.9}]
    with patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS), \
         patch("backend.agents.job_scout.llm.complete", return_value=_score_response(scored)) as mock_llm:
        run_job_scout(PREFERENCES)
    messages = mock_llm.call_args.kwargs["messages"]
    combined = json.dumps(messages)
    assert "Senior Python Engineer" in combined
    assert "Acme" in combined


def test_run_job_scout_returns_jobs_above_threshold():
    scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.85}]
    with patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS), \
         patch("backend.agents.job_scout.llm.complete", return_value=_score_response(scored)), \
         patch("backend.agents.job_scout.settings") as mock_settings:
        mock_settings.SCOUT_MODEL = "openai/gpt-4o-mini"
        mock_settings.JOB_MATCH_THRESHOLD = 0.6
        result = run_job_scout(PREFERENCES)
    assert len(result) == 1
    assert result[0]["match_score"] == 0.85


def test_run_job_scout_filters_jobs_below_threshold():
    scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.3}]
    with patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS), \
         patch("backend.agents.job_scout.llm.complete", return_value=_score_response(scored)), \
         patch("backend.agents.job_scout.settings") as mock_settings:
        mock_settings.SCOUT_MODEL = "openai/gpt-4o-mini"
        mock_settings.JOB_MATCH_THRESHOLD = 0.6
        result = run_job_scout(PREFERENCES)
    assert result == []


def test_run_job_scout_handles_malformed_llm_response():
    """Non-JSON LLM response returns empty list gracefully."""
    with patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS), \
         patch("backend.agents.job_scout.llm.complete",
               return_value=LLMResponse(content="Sorry, no jobs found.", tool_calls=[])):
        result = run_job_scout(PREFERENCES)
    assert result == []
