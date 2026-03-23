import pytest
from unittest.mock import patch
from backend.models import Job, Outreach


@pytest.fixture
def job(db_session):
    j = Job(title="Python Eng", company="Acme", url="https://acme.com/1", source="serpapi", status="new")
    db_session.add(j)
    db_session.commit()
    db_session.refresh(j)
    return j


def test_post_outreach_triggers_flow(client, job):
    mock_result = {
        "hr_name": "Jane Smith", "hr_email": "jane@acme.com",
        "hr_confidence": "search_result", "cover_letter": "Dear Jane...",
        "resume_version_path": "uploads/tailored.pdf",
    }
    with patch("backend.routers.outreach.run_outreach", return_value=mock_result), \
         patch("backend.routers.outreach.get_resume_path", return_value="uploads/cv.txt"):
        response = client.post("/outreach", json={"job_id": job.id})
    assert response.status_code == 200
    assert response.json()["hr_email"] == "jane@acme.com"
    assert response.json()["status"] == "draft"


def test_get_outreach(client, db_session, job):
    o = Outreach(job_id=job.id, hr_email="jane@acme.com", status="draft")
    db_session.add(o)
    db_session.commit()
    response = client.get("/outreach")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_patch_outreach_edits_draft(client, db_session, job):
    o = Outreach(job_id=job.id, hr_email="old@acme.com", cover_letter="Old letter", status="draft")
    db_session.add(o)
    db_session.commit()
    response = client.patch(f"/outreach/{o.id}", json={"hr_email": "new@acme.com", "cover_letter": "New letter"})
    assert response.status_code == 200
    assert response.json()["hr_email"] == "new@acme.com"
    # status must remain draft — PATCH cannot set it to sent
    assert response.json()["status"] == "draft"


def test_send_outreach_dispatches_email(client, db_session, job):
    o = Outreach(job_id=job.id, hr_email="jane@acme.com", cover_letter="Dear Jane...",
                 resume_version_path="uploads/t.pdf", status="draft")
    db_session.add(o)
    db_session.commit()
    with patch("backend.routers.outreach.send_email", return_value=True):
        response = client.post(f"/outreach/{o.id}/send")
    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    assert response.json()["sent_at"] is not None


def test_send_outreach_requires_email_address(client, db_session, job):
    o = Outreach(job_id=job.id, hr_email="", cover_letter="Dear...", status="draft")
    db_session.add(o)
    db_session.commit()
    response = client.post(f"/outreach/{o.id}/send")
    assert response.status_code == 400


def test_send_outreach_sets_job_error_on_send_failure(client, db_session, job):
    o = Outreach(job_id=job.id, hr_email="jane@acme.com", cover_letter="Dear Jane...", status="draft")
    db_session.add(o)
    db_session.commit()
    with patch("backend.routers.outreach.send_email", side_effect=Exception("SMTP failure")):
        response = client.post(f"/outreach/{o.id}/send")
    assert response.status_code == 500
    db_session.refresh(job)
    assert job.status == "error"
