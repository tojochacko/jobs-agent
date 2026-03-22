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
        poll_interval_hrs=6,
    )
    db.add(pref)
    db.commit()
    db.refresh(pref)
    assert pref.id is not None
    assert pref.poll_interval_hrs == 6


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
