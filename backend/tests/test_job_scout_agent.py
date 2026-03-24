# backend/tests/test_job_scout_agent.py
import json
import pytest
from unittest.mock import patch
from backend.llm import LLMResponse, ToolCall

PREFERENCES = {
    "job_titles": ["Python Engineer"],
    "location": "Remote",
    "remote_hybrid": "remote",
    "experience_level": "senior",
    "domain": "backend",
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


def _tool_use_response(tool_id, tool_input):
    return LLMResponse(
        content=None,
        tool_calls=[ToolCall(id=tool_id, name="search_jobs", arguments=tool_input)],
    )


def _end_turn_response(scored_jobs):
    return LLMResponse(content=json.dumps(scored_jobs), tool_calls=[])


def test_run_job_scout_returns_scored_jobs():
    scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.9}]
    with patch("backend.agents.job_scout.llm.complete") as mock_complete, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS):
        mock_complete.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer", "location": "Remote"}),
            _end_turn_response(scored),
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert len(result) == 1
    assert result[0]["match_score"] == 0.9


def test_run_job_scout_filters_below_threshold():
    low_scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.3}]
    with patch("backend.agents.job_scout.llm.complete") as mock_complete, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS), \
         patch("backend.agents.job_scout.settings") as mock_settings:
        mock_settings.SCOUT_MODEL = "anthropic/claude-haiku-4-5"
        mock_settings.JOB_MATCH_THRESHOLD = 0.6
        mock_complete.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer", "location": "Remote"}),
            _end_turn_response(low_scored),
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert result == []


def test_run_job_scout_handles_malformed_response():
    """Agent returns non-JSON text — should return empty list gracefully."""
    with patch("backend.agents.job_scout.llm.complete") as mock_complete, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS):
        mock_complete.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer"}),
            LLMResponse(content="Sorry, I could not find any jobs.", tool_calls=[]),
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert result == []
