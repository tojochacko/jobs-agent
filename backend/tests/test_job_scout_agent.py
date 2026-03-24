import json
import pytest
from unittest.mock import patch, MagicMock

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
    tc = MagicMock()
    tc.id = tool_id
    tc.function.name = "search_jobs"
    tc.function.arguments = json.dumps(tool_input)
    msg = MagicMock()
    msg.tool_calls = [tc]
    msg.content = None
    choice = MagicMock()
    choice.finish_reason = "tool_calls"
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _end_turn_response(scored_jobs):
    msg = MagicMock()
    msg.content = json.dumps(scored_jobs)
    msg.tool_calls = None
    choice = MagicMock()
    choice.finish_reason = "stop"
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_run_job_scout_returns_scored_jobs():
    scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.9}]
    with patch("backend.agents.job_scout.litellm.completion") as mock_completion, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS):
        mock_completion.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer", "location": "Remote"}),
            _end_turn_response(scored),
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert len(result) == 1
    assert result[0]["match_score"] == 0.9


def test_run_job_scout_filters_below_threshold():
    low_scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.3}]
    with patch("backend.agents.job_scout.litellm.completion") as mock_completion, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS), \
         patch("backend.agents.job_scout.settings") as mock_settings:
        mock_settings.SCOUT_MODEL = "anthropic/claude-haiku-4-5"
        mock_settings.JOB_MATCH_THRESHOLD = 0.6
        mock_completion.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer", "location": "Remote"}),
            _end_turn_response(low_scored),
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert result == []


def test_run_job_scout_handles_malformed_response():
    """Agent returns non-JSON text — should return empty list gracefully."""
    msg = MagicMock()
    msg.content = "Sorry, I could not find any jobs."
    msg.tool_calls = None
    choice = MagicMock()
    choice.finish_reason = "stop"
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    with patch("backend.agents.job_scout.litellm.completion") as mock_completion, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS):
        mock_completion.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer"}),
            resp,
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert result == []
