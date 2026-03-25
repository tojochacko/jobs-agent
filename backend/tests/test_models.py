# backend/tests/test_models.py
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from backend.models import Application, OAuthToken, Outreach, Preference, Resume, Job


def test_create_preference(db_session):
    pref = Preference(
        job_titles='["Python Engineer"]',
        location="Remote",
        remote_hybrid="remote",
        experience_level="senior",
        domain="backend",
        company_size='["startup"]',
    )
    db_session.add(pref)
    db_session.commit()
    db_session.refresh(pref)
    assert pref.id is not None
    assert not hasattr(pref, "poll_interval_hrs")


def test_create_resume(db_session):
    resume = Resume(filename="cv.pdf", filepath="uploads/cv.pdf")
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    assert resume.id is not None
    assert resume.filepath == "uploads/cv.pdf"


def test_create_job(db_session):
    job = Job(
        title="Python Engineer",
        company="Acme",
        url="https://acme.com/jobs/1",
        description="Build cool things",
        location="Remote",
        match_score=0.85,
        source="serpapi",
        status="new",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    assert job.id is not None
    assert job.match_score == 0.85
    assert job.status == "new"


def test_job_url_unique(db_session):
    db_session.add(Job(title="Eng", company="A", url="https://a.com/1", source="serpapi"))
    db_session.commit()
    db_session.add(Job(title="Eng", company="B", url="https://a.com/1", source="serpapi"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_create_application(db_session):
    job = Job(title="Eng", company="A", url="https://a.com/1", source="serpapi")
    db_session.add(job)
    db_session.commit()

    app = Application(
        job_id=job.id,
        tailored_resume_path="uploads/tailored_1.txt",
        form_payload='{"first_name": "John"}',
        status="pending",
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)
    assert app.id is not None
    assert app.status == "pending"
    assert app.applied_at is None  # NULL until user confirms submission


def test_create_oauth_token(db_session):
    token = OAuthToken(
        provider="gmail",
        access_token="access_abc",
        refresh_token="refresh_xyz",
        expires_at=datetime(2026, 12, 31),
    )
    db_session.add(token)
    db_session.commit()
    db_session.refresh(token)
    assert token.id is not None
    assert token.provider == "gmail"


def test_create_outreach(db_session):
    job = Job(title="Eng", company="A", url="https://a.com/1", source="serpapi")
    db_session.add(job)
    db_session.commit()
    outreach = Outreach(
        job_id=job.id, hr_name="Jane Smith", hr_email="jane@acme.com",
        hr_confidence="search_result", cover_letter="Dear Jane...", status="draft",
    )
    db_session.add(outreach)
    db_session.commit()
    db_session.refresh(outreach)
    assert outreach.id is not None
    assert outreach.sent_at is None  # NULL until sent
