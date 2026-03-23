import pytest
from unittest.mock import patch
from backend.models import Job


VALID_PAYLOAD = {
    "source": "gmail-agent",
    "jobs": [
        {
            "title": "Python Engineer",
            "company": "Acme Corp",
            "url": "https://acme.com/jobs/webhook-1",
            "description": "Build APIs",
            "location": "Remote",
        }
    ],
}


@pytest.fixture
def webhook_headers(monkeypatch):
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_SECRET", "test-secret")
    return {"X-Webhook-Secret": "test-secret"}


def test_webhook_requires_secret(client, monkeypatch):
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_SECRET", "test-secret")
    response = client.post("/webhook/job-alerts", json=VALID_PAYLOAD)
    assert response.status_code == 401


def test_webhook_rejects_wrong_secret(client, monkeypatch):
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_SECRET", "correct-secret")
    response = client.post(
        "/webhook/job-alerts",
        json=VALID_PAYLOAD,
        headers={"X-Webhook-Secret": "wrong-secret"},
    )
    assert response.status_code == 401


def test_webhook_persists_matching_jobs(client, db_session, webhook_headers, monkeypatch):
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_SECRET", "test-secret")
    with patch("backend.routers.webhook.score_job", return_value=0.85), \
         patch("backend.routers.webhook.get_preferences_dict",
               return_value={"job_titles": ["Python Engineer"]}):
        response = client.post("/webhook/job-alerts", json=VALID_PAYLOAD, headers=webhook_headers)
    assert response.status_code == 200
    assert response.json()["inserted"] == 1
    jobs = db_session.query(Job).all()
    assert len(jobs) == 1
    assert jobs[0].source == "webhook"
    assert jobs[0].match_score == 0.85


def test_webhook_skips_low_score(client, db_session, webhook_headers, monkeypatch):
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("backend.routers.webhook.settings.JOB_MATCH_THRESHOLD", 0.6)
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_BYPASS_THRESHOLD", False)
    with patch("backend.routers.webhook.score_job", return_value=0.3), \
         patch("backend.routers.webhook.get_preferences_dict",
               return_value={"job_titles": ["Python Engineer"]}):
        response = client.post("/webhook/job-alerts", json=VALID_PAYLOAD, headers=webhook_headers)
    assert response.status_code == 200
    assert response.json()["inserted"] == 0


def test_webhook_bypass_threshold_stores_all(client, db_session, webhook_headers, monkeypatch):
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_BYPASS_THRESHOLD", True)
    with patch("backend.routers.webhook.score_job", return_value=0.2), \
         patch("backend.routers.webhook.get_preferences_dict",
               return_value={"job_titles": ["Python Engineer"]}):
        response = client.post("/webhook/job-alerts", json=VALID_PAYLOAD, headers=webhook_headers)
    assert response.status_code == 200
    assert response.json()["inserted"] == 1


def test_webhook_deduplicates_by_url(client, db_session, webhook_headers, monkeypatch):
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_SECRET", "test-secret")
    existing = Job(
        title="Python Engineer", company="Acme", url="https://acme.com/jobs/webhook-1",
        source="webhook",
    )
    db_session.add(existing)
    db_session.commit()
    with patch("backend.routers.webhook.score_job", return_value=0.9), \
         patch("backend.routers.webhook.get_preferences_dict",
               return_value={"job_titles": ["Python Engineer"]}):
        response = client.post("/webhook/job-alerts", json=VALID_PAYLOAD, headers=webhook_headers)
    assert response.status_code == 200
    assert response.json()["inserted"] == 0
    assert db_session.query(Job).count() == 1  # no duplicate


def test_webhook_proceeds_without_preferences(client, db_session, webhook_headers, monkeypatch):
    """If no preferences configured and bypass=True, all incoming jobs are stored with score=0.0."""
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_BYPASS_THRESHOLD", True)
    with patch("backend.routers.webhook.get_preferences_dict", return_value=None), \
         patch("backend.routers.webhook.score_job", return_value=0.0):
        response = client.post("/webhook/job-alerts", json=VALID_PAYLOAD, headers=webhook_headers)
    assert response.status_code == 200
    assert response.json()["inserted"] == 1   # job is stored despite no preferences
    assert db_session.query(Job).count() == 1
