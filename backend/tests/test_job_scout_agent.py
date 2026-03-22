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
    block = MagicMock()
    block.type = "tool_use"
    block.name = "search_jobs"
    block.id = tool_id
    block.input = tool_input
    resp = MagicMock()
    resp.stop_reason = "tool_use"
    resp.content = [block]
    return resp


def _end_turn_response(scored_jobs):
    block = MagicMock()
    block.type = "text"
    block.text = json.dumps(scored_jobs)
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    resp.content = [block]
    return resp


def test_run_job_scout_returns_scored_jobs():
    scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.9}]
    with patch("backend.agents.job_scout.anthropic.Anthropic") as MockClient, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS):
        client = MagicMock()
        MockClient.return_value = client
        client.messages.create.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer", "location": "Remote"}),
            _end_turn_response(scored),
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert len(result) == 1
    assert result[0]["match_score"] == 0.9


def test_run_job_scout_filters_below_threshold():
    low_scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.3}]
    with patch("backend.agents.job_scout.anthropic.Anthropic") as MockClient, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS), \
         patch("backend.agents.job_scout.settings") as mock_settings:
        mock_settings.SCOUT_MODEL = "claude-haiku-4-5"
        mock_settings.ANTHROPIC_API_KEY = "test"
        mock_settings.JOB_MATCH_THRESHOLD = 0.6
        client = MagicMock()
        MockClient.return_value = client
        client.messages.create.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer", "location": "Remote"}),
            _end_turn_response(low_scored),
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert result == []


def test_run_job_scout_handles_malformed_response():
    """Agent returns non-JSON text — should return empty list gracefully."""
    with patch("backend.agents.job_scout.anthropic.Anthropic") as MockClient, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS):
        client = MagicMock()
        MockClient.return_value = client
        block = MagicMock()
        block.type = "text"
        block.text = "Sorry, I could not find any jobs."
        resp = MagicMock()
        resp.stop_reason = "end_turn"
        resp.content = [block]
        client.messages.create.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer"}),
            resp,
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert result == []
