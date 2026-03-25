# backend/tests/test_orchestrator.py
from unittest.mock import patch
from backend.llm import LLMResponse, ToolCall
from backend.agents.orchestrator import score_job

PREFERENCES = {
    "job_titles": ["Python Engineer"],
    "location": "Remote",
    "remote_hybrid": "remote",
    "experience_level": "senior",
    "domain": "backend",
    "company_size": ["startup"],
}

HIGH_MATCH_JOB = {
    "title": "Senior Python Engineer",
    "company": "Startup Co",
    "location": "Remote",
    "description": "FastAPI, PostgreSQL, Docker, fully remote senior backend role",
    "url": "https://startup.com/jobs/1",
}

LOW_MATCH_JOB = {
    "title": "Junior Marketing Analyst",
    "company": "Big Corp",
    "location": "New York",
    "description": "Excel, PowerPoint, marketing campaigns",
    "url": "https://bigcorp.com/jobs/2",
}


def test_score_job_returns_float():
    with patch("backend.agents.orchestrator.llm.complete") as mock_complete:
        mock_complete.return_value = LLMResponse(content="0.92")
        score = score_job(HIGH_MATCH_JOB, PREFERENCES)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
    assert score == 0.92


def test_score_job_handles_malformed_response():
    with patch("backend.agents.orchestrator.llm.complete") as mock_complete:
        mock_complete.return_value = LLMResponse(content="I cannot score this job.")
        score = score_job(LOW_MATCH_JOB, PREFERENCES)
    assert score == 0.0


def test_score_job_clamps_to_valid_range():
    with patch("backend.agents.orchestrator.llm.complete") as mock_complete:
        mock_complete.return_value = LLMResponse(content="1.5")
        score = score_job(HIGH_MATCH_JOB, PREFERENCES)
    assert score == 1.0
