import pytest
from unittest.mock import patch, MagicMock
from backend.models import Job


def test_run_poll_calls_job_scout_when_preferences_exist():
    with patch("backend.scheduler.run_job_scout") as mock_scout, \
         patch("backend.scheduler.get_preferences_dict", return_value={"job_titles": ["Engineer"]}), \
         patch("backend.scheduler.SessionLocal"):
        mock_scout.return_value = []
        from backend.scheduler import run_poll
        run_poll()
        mock_scout.assert_called_once()


def test_run_poll_skips_when_no_preferences():
    with patch("backend.scheduler.run_job_scout") as mock_scout, \
         patch("backend.scheduler.get_preferences_dict", return_value=None):
        from backend.scheduler import run_poll
        run_poll()
        mock_scout.assert_not_called()


def test_run_poll_persists_new_jobs(db_session):
    new_jobs = [
        {"title": "Eng", "company": "A", "url": "https://a.com/1",
         "location": "Remote", "description": "desc", "match_score": 0.8}
    ]
    with patch("backend.scheduler.run_job_scout", return_value=new_jobs), \
         patch("backend.scheduler.get_preferences_dict", return_value={"job_titles": ["Eng"]}), \
         patch("backend.scheduler.SessionLocal") as mock_session_local:
        mock_session_local.return_value = db_session
        from backend.scheduler import run_poll
        run_poll()
    jobs = db_session.query(Job).all()
    assert len(jobs) == 1
    assert jobs[0].source == "serpapi"
    assert jobs[0].match_score == 0.8


def test_run_poll_deduplicates_by_url(db_session):
    """Running poll twice with same job URL only stores it once."""
    existing = Job(title="Eng", company="A", url="https://a.com/1", source="serpapi")
    db_session.add(existing)
    db_session.commit()

    new_jobs = [{"title": "Eng", "company": "A", "url": "https://a.com/1",
                 "location": "Remote", "description": "desc", "match_score": 0.8}]
    with patch("backend.scheduler.run_job_scout", return_value=new_jobs), \
         patch("backend.scheduler.get_preferences_dict", return_value={"job_titles": ["Eng"]}), \
         patch("backend.scheduler.SessionLocal") as mock_session_local:
        mock_session_local.return_value = db_session
        from backend.scheduler import run_poll
        run_poll()
    assert db_session.query(Job).count() == 1
