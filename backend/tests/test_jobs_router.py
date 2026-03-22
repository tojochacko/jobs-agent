import pytest
from backend.models import Job


@pytest.fixture
def seed_jobs(db_session):
    jobs = [
        Job(title="Python Engineer", company="Acme", url="https://acme.com/1",
            source="serpapi", match_score=0.9, status="new"),
        Job(title="Backend Engineer", company="Beta", url="https://beta.com/2",
            source="serpapi", match_score=0.75, status="saved"),
        Job(title="Old Job", company="Gamma", url="https://gamma.com/3",
            source="webhook", match_score=0.5, status="dismissed"),
    ]
    for j in jobs:
        db_session.add(j)
    db_session.commit()


def test_list_jobs(client, seed_jobs):
    response = client.get("/jobs")
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_get_job_by_id(client, seed_jobs, db_session):
    job = db_session.query(Job).first()
    response = client.get(f"/jobs/{job.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Python Engineer"


def test_get_job_not_found(client):
    response = client.get("/jobs/9999")
    assert response.status_code == 404


def test_delete_job(client, seed_jobs, db_session):
    job = db_session.query(Job).filter_by(company="Gamma").first()
    response = client.delete(f"/jobs/{job.id}")
    assert response.status_code == 200
    assert client.get(f"/jobs/{job.id}").status_code == 404


def test_refresh_jobs_endpoint(client):
    """POST /jobs/refresh triggers poll and returns 200."""
    from unittest.mock import patch
    with patch("backend.routers.jobs.run_poll") as mock_poll:
        response = client.post("/jobs/refresh")
        assert response.status_code == 200
        mock_poll.assert_called_once()
