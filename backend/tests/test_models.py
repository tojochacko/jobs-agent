# backend/tests/test_models.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.database import Base
from backend.models import Preference, Resume, Job


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_create_preference(db):
    pref = Preference(
        job_titles='["Python Engineer"]',
        location="Remote",
        remote_hybrid="remote",
        experience_level="senior",
        domain="backend",
        company_size='["startup"]',
    )
    db.add(pref)
    db.commit()
    db.refresh(pref)
    assert pref.id is not None
    assert not hasattr(pref, "poll_interval_hrs")


def test_create_resume(db):
    resume = Resume(filename="cv.pdf", filepath="uploads/cv.pdf")
    db.add(resume)
    db.commit()
    db.refresh(resume)
    assert resume.id is not None
    assert resume.filepath == "uploads/cv.pdf"


def test_create_job(db):
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
    db.add(job)
    db.commit()
    db.refresh(job)
    assert job.id is not None
    assert job.match_score == 0.85
    assert job.status == "new"


def test_job_url_unique(db):
    db.add(Job(title="Eng", company="A", url="https://a.com/1", source="serpapi"))
    db.commit()
    db.add(Job(title="Eng", company="B", url="https://a.com/1", source="serpapi"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_create_application(db):
    from backend.models import Application
    job = Job(title="Eng", company="A", url="https://a.com/1", source="serpapi")
    db.add(job)
    db.commit()

    app = Application(
        job_id=job.id,
        tailored_resume_path="uploads/tailored_1.txt",
        form_payload='{"first_name": "John"}',
        status="pending",
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    assert app.id is not None
    assert app.status == "pending"
    assert app.applied_at is None  # NULL until user confirms submission


def test_create_oauth_token(db):
    from backend.models import OAuthToken
    from datetime import datetime
    token = OAuthToken(
        provider="gmail",
        access_token="access_abc",
        refresh_token="refresh_xyz",
        expires_at=datetime(2026, 12, 31),
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    assert token.id is not None
    assert token.provider == "gmail"


def test_create_outreach(db):
    from backend.models import Outreach
    job = Job(title="Eng", company="A", url="https://a.com/1", source="serpapi")
    db.add(job)
    db.commit()
    outreach = Outreach(
        job_id=job.id, hr_name="Jane Smith", hr_email="jane@acme.com",
        hr_confidence="search_result", cover_letter="Dear Jane...", status="draft",
    )
    db.add(outreach)
    db.commit()
    db.refresh(outreach)
    assert outreach.id is not None
    assert outreach.sent_at is None  # NULL until sent
