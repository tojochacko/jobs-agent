from unittest.mock import patch, MagicMock

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


def _mock_score_response(score: float):
    block = MagicMock(type="text", text=str(score))
    resp = MagicMock(stop_reason="end_turn", content=[block])
    return resp


def test_score_job_returns_float():
    with patch("backend.agents.orchestrator.anthropic.Anthropic") as MockClient:
        client = MagicMock()
        MockClient.return_value = client
        client.messages.create.return_value = _mock_score_response(0.92)
        from backend.agents.orchestrator import score_job
        score = score_job(HIGH_MATCH_JOB, PREFERENCES)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
    assert score == 0.92


def test_score_job_handles_malformed_response():
    """If agent returns non-numeric text, return 0.0 safely."""
    block = MagicMock(type="text", text="I cannot score this job.")
    resp = MagicMock(stop_reason="end_turn", content=[block])
    with patch("backend.agents.orchestrator.anthropic.Anthropic") as MockClient:
        client = MagicMock()
        MockClient.return_value = client
        client.messages.create.return_value = resp
        from backend.agents.orchestrator import score_job
        score = score_job(LOW_MATCH_JOB, PREFERENCES)
    assert score == 0.0


def test_score_job_clamps_to_valid_range():
    """Scores outside 0.0–1.0 are clamped."""
    with patch("backend.agents.orchestrator.anthropic.Anthropic") as MockClient:
        client = MagicMock()
        MockClient.return_value = client
        client.messages.create.return_value = _mock_score_response(1.5)
        from backend.agents.orchestrator import score_job
        score = score_job(HIGH_MATCH_JOB, PREFERENCES)
    assert score == 1.0
