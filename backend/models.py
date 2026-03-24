from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, UniqueConstraint
from backend.database import Base


class Preference(Base):
    __tablename__ = "preferences"
    id = Column(Integer, primary_key=True)
    job_titles = Column(Text, nullable=False)        # JSON string
    location = Column(String)
    remote_hybrid = Column(String)                   # 'remote'|'hybrid'|'onsite'|'any'
    experience_level = Column(String)
    domain = Column(String)
    company_size = Column(Text)                      # JSON string
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Resume(Base):
    __tablename__ = "resume"
    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)        # path on disk
    uploaded_at = Column(DateTime, default=datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    url = Column(String, nullable=False, unique=True)
    description = Column(Text)
    location = Column(String)
    match_score = Column(Float)
    source = Column(String, nullable=False)          # 'serpapi'|'webhook'
    # 'new'|'saved'|'dismissed'|'applying'|'applied'|'emailing'|'emailed'|'error'
    status = Column(String, default="new")
    error_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("url", name="uq_jobs_url"),)


class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, nullable=False)        # FK to jobs.id
    tailored_resume_path = Column(Text)             # path on disk (text output for forms)
    form_payload = Column(Text)                     # JSON: {field_name: prefilled_value}
    tailored_resume_text = Column(Text)             # text content for frontend diff display
    # 'pending'|'reviewing'|'submitted'|'rejected'|'interviewing'|'offered'|'manual_required'
    status = Column(String, default="pending")
    notes = Column(Text)
    applied_at = Column(DateTime, nullable=True)    # NULL until user confirms submission


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    id = Column(Integer, primary_key=True)
    provider = Column(String, nullable=False, unique=True)   # 'gmail' | 'outlook'
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Outreach(Base):
    __tablename__ = "outreach"
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, nullable=False)
    hr_name = Column(String)
    hr_email = Column(String)
    hr_confidence = Column(String)               # 'search_result'|'inferred_pattern'|'unknown'
    cover_letter = Column(Text)
    resume_version_path = Column(String)         # path to tailored PDF
    status = Column(String, default="draft")     # 'draft' | 'sent'
    sent_at = Column(DateTime, nullable=True)    # NULL until sent
