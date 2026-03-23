import json
import pytest
from unittest.mock import patch
from backend.models import Job, Application


@pytest.fixture
def job(db_session):
    j = Job(title="Python Eng", company="Acme", url="https://acme.com/1", source="serpapi", status="new")
    db_session.add(j)
    db_session.commit()
    db_session.refresh(j)
    return j


def test_post_applications_triggers_flow(client, job, db_session):
    mock_result = {
        "status": "ready",
        "form_payload": {"first_name": "John"},
        "tailored_resume": "Tailored resume",
        "form_fields": [],
        "url": "https://acme.com/1",
    }
    with patch("backend.routers.applications.run_applicator", return_value=mock_result), \
         patch("backend.routers.applications.get_resume_path", return_value="uploads/cv.txt"):
        response = client.post("/applications", json={"job_id": job.id})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    # jobs.status should transition to 'applying'
    db_session.refresh(job)
    assert job.status == "applying"


def test_post_applications_blocks_duplicate(client, job, db_session):
    """Second trigger while job is already 'applying' should return 409."""
    job.status = "applying"
    db_session.commit()
    response = client.post("/applications", json={"job_id": job.id})
    assert response.status_code == 409


def test_post_applications_manual_required(client, job, db_session):
    mock_result = {"status": "manual_required", "url": "https://acme.com/1"}
    with patch("backend.routers.applications.run_applicator", return_value=mock_result), \
         patch("backend.routers.applications.get_resume_path", return_value="uploads/cv.txt"):
        response = client.post("/applications", json={"job_id": job.id})
    assert response.status_code == 200
    assert response.json()["status"] == "manual_required"


def test_get_applications(client, db_session, job):
    app = Application(job_id=job.id, status="pending")
    db_session.add(app)
    db_session.commit()
    response = client.get("/applications")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_patch_application_status_submitted(client, db_session, job):
    app = Application(job_id=job.id, status="reviewing")
    db_session.add(app)
    db_session.commit()
    response = client.patch(f"/applications/{app.id}", json={"status": "submitted"})
    assert response.status_code == 200
    assert response.json()["status"] == "submitted"
    assert response.json()["applied_at"] is not None
    db_session.refresh(job)
    assert job.status == "applied"


def test_patch_application_not_found(client):
    response = client.patch("/applications/9999", json={"status": "submitted"})
    assert response.status_code == 404
