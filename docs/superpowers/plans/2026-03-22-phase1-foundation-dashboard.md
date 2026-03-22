# Phase 1: Foundation + Job Discovery Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the project foundation — FastAPI backend with SQLite, JobScout Agent using SerpAPI + Claude Haiku, APScheduler polling, and a React dashboard showing matched jobs.

**Architecture:** Single-user FastAPI backend with SQLAlchemy + SQLite. JobScout Agent uses the Anthropic SDK tool-use agentic loop to call SerpAPI, score results (0.0–1.0) against user preferences, and persist matching jobs above `JOB_MATCH_THRESHOLD`. APScheduler polls on startup and on the configured interval. React + Vite frontend communicates via REST.

**Tech Stack:** Python 3.12, FastAPI 0.115+, SQLAlchemy 2.0, SQLite, anthropic>=0.40, requests, APScheduler 3.x, pydantic-settings, pytest, httpx, React 18, Vite 5, Vitest, @testing-library/react

**Spec:** `docs/superpowers/specs/2026-03-22-job-applier-agent-design.md`

---

## File Map

### Backend

| File | Responsibility |
|---|---|
| `backend/requirements.txt` | Python dependencies |
| `backend/config.py` | Typed settings via pydantic-settings; reads from `.env` |
| `backend/database.py` | SQLAlchemy engine, session factory, `get_db` dependency |
| `backend/models.py` | ORM models: `Preference`, `Resume`, `Job` |
| `backend/tools/serp.py` | `search_jobs(query, location, num_results)` — calls SerpAPI Google Jobs |
| `backend/agents/job_scout.py` | `run_job_scout(preferences)` — Anthropic tool-use agentic loop; returns scored job dicts |
| `backend/routers/preferences.py` | `GET /preferences`, `POST /preferences` |
| `backend/routers/resume.py` | `POST /resume`, `GET /resume` |
| `backend/routers/jobs.py` | `GET /jobs`, `GET /jobs/{id}`, `DELETE /jobs/{id}`, `POST /jobs/refresh` |
| `backend/scheduler.py` | `run_poll()`, `start_scheduler(poll_interval_hrs)` |
| `backend/main.py` | FastAPI app, mounts routers, starts scheduler via lifespan |
| `backend/tests/conftest.py` | `client`, `db_session`, `db_engine` fixtures |
| `backend/tests/fixtures/serp_response.json` | Recorded SerpAPI response for offline tests |
| `backend/tests/test_config.py` | Unit tests for settings loading |
| `backend/tests/test_models.py` | Unit tests for ORM model creation + constraints |
| `backend/tests/test_serp_tool.py` | Unit tests for `search_jobs` with mocked HTTP |
| `backend/tests/test_job_scout_agent.py` | Unit tests for `run_job_scout` with mocked Anthropic client |
| `backend/tests/test_preferences_router.py` | API tests for preferences routes |
| `backend/tests/test_resume_router.py` | API tests for resume upload |
| `backend/tests/test_jobs_router.py` | API tests for jobs routes |
| `backend/tests/test_scheduler.py` | Unit tests for scheduler poll logic |
| `backend/tests/test_main.py` | App assembly smoke tests |

### Frontend

| File | Responsibility |
|---|---|
| `frontend/package.json` | Dependencies: react, react-router-dom, axios, vitest, @testing-library/react |
| `frontend/vite.config.js` | Vite + proxy to backend `:8000` + Vitest config |
| `frontend/src/test-setup.js` | `@testing-library/jest-dom` import |
| `frontend/src/main.jsx` | React entry point |
| `frontend/src/App.jsx` | Router: Dashboard `/`, Preferences `/preferences` |
| `frontend/src/api/client.js` | axios wrappers: `getJobs`, `getJob`, `deleteJob`, `getPreferences`, `savePreferences`, `uploadResume`, `refreshJobs` |
| `frontend/src/components/StatusBadge.jsx` | Color-coded badge for job status and match score |
| `frontend/src/components/JobCard.jsx` | One job: title, company, badges, JD preview, action buttons |
| `frontend/src/pages/Dashboard.jsx` | Loads jobs, renders cards, Refresh Now button |
| `frontend/src/pages/Preferences.jsx` | Criteria form + resume upload |

---

## Tasks

---

### Task 1: Backend Scaffolding

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: directory structure

- [ ] **Step 1: Create backend directory structure**

```bash
mkdir -p backend/tools backend/agents backend/routers backend/tests/fixtures uploads
touch backend/__init__.py backend/tools/__init__.py backend/agents/__init__.py \
      backend/routers/__init__.py backend/tests/__init__.py uploads/.gitkeep
```

- [ ] **Step 2: Create `backend/requirements.txt`**

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
sqlalchemy==2.0.36
pydantic-settings==2.6.1
python-multipart==0.0.12
anthropic>=0.40.0
requests==2.32.3
apscheduler==3.10.4
httpx==0.27.2
pytest==8.3.3
pytest-mock==3.14.0
```

- [ ] **Step 3: Create `backend/.env.example`**

```bash
# LLM
ANTHROPIC_API_KEY=
ORCHESTRATOR_MODEL=claude-haiku-4-5
SCOUT_MODEL=claude-haiku-4-5
APPLICATOR_MODEL=claude-haiku-4-5
OUTREACH_MODEL=claude-haiku-4-5

# Job Discovery
SERP_API_KEY=
JOB_MATCH_THRESHOLD=0.6
WEBHOOK_BYPASS_THRESHOLD=false

# Email (Phase 3)
EMAIL_PROVIDER=gmail
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
OUTLOOK_CLIENT_ID=
OUTLOOK_CLIENT_SECRET=
OAUTH_REDIRECT_URI=http://localhost:8000/auth/email/callback

# Webhook
WEBHOOK_SECRET=

# Database
DATABASE_URL=sqlite:///./jobapplier.db

# File Storage
UPLOAD_DIR=uploads
```

- [ ] **Step 4: Create `.gitignore`**

```
.env
*.db
uploads/*
!uploads/.gitkeep
__pycache__/
.pytest_cache/
node_modules/
dist/
.venv/
```

- [ ] **Step 5: Install dependencies**

```bash
cd backend && pip install -r requirements.txt
```

Expected: All packages install without error.

- [ ] **Step 6: Commit**

```bash
git add backend/ uploads/.gitkeep .gitignore
git commit -m "chore: scaffold backend project structure"
```

---

### Task 2: Config

**Files:**
- Create: `backend/config.py`
- Create: `backend/tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_config.py
import os
import pytest
from unittest.mock import patch


def test_settings_load_from_env():
    env = {
        "ANTHROPIC_API_KEY": "test-key",
        "SERP_API_KEY": "serp-key",
        "SCOUT_MODEL": "claude-haiku-4-5",
        "JOB_MATCH_THRESHOLD": "0.7",
        "DATABASE_URL": "sqlite:///./test.db",
        "UPLOAD_DIR": "uploads",
    }
    with patch.dict(os.environ, env, clear=True):
        from importlib import reload
        import backend.config as cfg
        reload(cfg)
        s = cfg.Settings()
        assert s.ANTHROPIC_API_KEY == "test-key"
        assert s.JOB_MATCH_THRESHOLD == 0.7
        assert s.SCOUT_MODEL == "claude-haiku-4-5"


def test_default_values():
    env = {
        "ANTHROPIC_API_KEY": "key",
        "SERP_API_KEY": "serp",
        "DATABASE_URL": "sqlite:///./test.db",
        "UPLOAD_DIR": "uploads",
    }
    with patch.dict(os.environ, env, clear=True):
        from importlib import reload
        import backend.config as cfg
        reload(cfg)
        s = cfg.Settings()
        assert s.JOB_MATCH_THRESHOLD == 0.6
        assert s.SCOUT_MODEL == "claude-haiku-4-5"
        assert s.WEBHOOK_BYPASS_THRESHOLD is False
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd backend && pytest tests/test_config.py -v
```

Expected: `ImportError: No module named 'backend.config'`

- [ ] **Step 3: Implement `backend/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str
    ORCHESTRATOR_MODEL: str = "claude-haiku-4-5"
    SCOUT_MODEL: str = "claude-haiku-4-5"
    APPLICATOR_MODEL: str = "claude-haiku-4-5"
    OUTREACH_MODEL: str = "claude-haiku-4-5"

    SERP_API_KEY: str = ""
    JOB_MATCH_THRESHOLD: float = 0.6
    WEBHOOK_BYPASS_THRESHOLD: bool = False

    EMAIL_PROVIDER: str = "gmail"
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    OUTLOOK_CLIENT_ID: str = ""
    OUTLOOK_CLIENT_SECRET: str = ""
    OAUTH_REDIRECT_URI: str = "http://localhost:8000/auth/email/callback"

    WEBHOOK_SECRET: str = ""

    DATABASE_URL: str = "sqlite:///./jobapplier.db"
    UPLOAD_DIR: str = "uploads"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

- [ ] **Step 4: Run test — expect pass**

```bash
cd backend && pytest tests/test_config.py -v
```

Expected: 2 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/config.py backend/tests/test_config.py
git commit -m "feat: add pydantic-settings config"
```

---

### Task 3: Database and Models

**Files:**
- Create: `backend/database.py`
- Create: `backend/models.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `backend/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from backend.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite only
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Implement `backend/models.py`**

```python
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
    poll_interval_hrs = Column(Integer, default=6)
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
```

- [ ] **Step 5: Run tests — expect pass**

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: 4 tests PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/database.py backend/models.py backend/tests/test_models.py
git commit -m "feat: add SQLAlchemy database and ORM models"
```

---

### Task 4: SerpAPI Tool

**Files:**
- Create: `backend/tools/serp.py`
- Create: `backend/tests/fixtures/serp_response.json`
- Create: `backend/tests/test_serp_tool.py`

- [ ] **Step 1: Create fixture `backend/tests/fixtures/serp_response.json`**

```json
{
  "jobs_results": [
    {
      "title": "Senior Python Engineer",
      "company_name": "Acme Corp",
      "location": "Remote",
      "description": "Build scalable APIs with Python and FastAPI.",
      "job_id": "abc123",
      "related_links": [{"link": "https://acme.com/careers/senior-python-engineer", "text": "Apply"}]
    },
    {
      "title": "Backend Engineer",
      "company_name": "Beta Inc",
      "location": "San Francisco, CA",
      "description": "Work on distributed systems at scale.",
      "job_id": "def456",
      "related_links": [{"link": "https://betainc.com/jobs/backend-engineer", "text": "Apply"}]
    }
  ]
}
```

- [ ] **Step 2: Write failing tests**

```python
# backend/tests/test_serp_tool.py
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "serp_response.json").read_text()
)


@pytest.fixture
def mock_requests():
    with patch("backend.tools.serp.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = FIXTURE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        yield mock_get


def test_search_jobs_returns_list(mock_requests):
    from backend.tools.serp import search_jobs
    results = search_jobs(query="Python Engineer", location="Remote")
    assert isinstance(results, list)
    assert len(results) == 2


def test_search_jobs_maps_fields(mock_requests):
    from backend.tools.serp import search_jobs
    results = search_jobs(query="Python Engineer", location="Remote")
    job = results[0]
    assert job["title"] == "Senior Python Engineer"
    assert job["company"] == "Acme Corp"
    assert job["location"] == "Remote"
    assert job["url"] == "https://acme.com/careers/senior-python-engineer"
    assert "description" in job


def test_search_jobs_raises_on_api_error():
    from backend.tools.serp import search_jobs
    with patch("backend.tools.serp.requests.get") as mock_get:
        mock_get.return_value.raise_for_status.side_effect = Exception("quota exceeded")
        with pytest.raises(Exception, match="quota exceeded"):
            search_jobs(query="Engineer")
```

- [ ] **Step 3: Run tests — expect failure**

```bash
cd backend && pytest tests/test_serp_tool.py -v
```

Expected: `ImportError: cannot import name 'search_jobs'`

- [ ] **Step 4: Implement `backend/tools/serp.py`**

```python
import requests
from backend.config import settings


def search_jobs(query: str, location: str = "", num_results: int = 10) -> list[dict]:
    """Call SerpAPI Google Jobs endpoint and return normalized job list."""
    params = {
        "engine": "google_jobs",
        "q": query,
        "location": location,
        "num": num_results,
        "api_key": settings.SERP_API_KEY,
    }
    response = requests.get("https://serpapi.com/search", params=params)
    response.raise_for_status()
    data = response.json()

    jobs = []
    for raw in data.get("jobs_results", []):
        links = raw.get("related_links", [])
        url = links[0].get("link", "") if links else ""
        jobs.append({
            "title": raw.get("title", ""),
            "company": raw.get("company_name", ""),
            "location": raw.get("location", ""),
            "description": raw.get("description", ""),
            "url": url,
        })
    return jobs


def search_people(query: str, num_results: int = 5) -> list[dict]:
    """Call SerpAPI Google Search for HR contact discovery."""
    params = {
        "engine": "google",
        "q": query,
        "num": num_results,
        "api_key": settings.SERP_API_KEY,
    }
    response = requests.get("https://serpapi.com/search", params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("organic_results", [])
```

- [ ] **Step 5: Run tests — expect pass**

```bash
cd backend && pytest tests/test_serp_tool.py -v
```

Expected: 3 tests PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/tools/serp.py backend/tests/test_serp_tool.py backend/tests/fixtures/
git commit -m "feat: add SerpAPI job search and people search tools"
```

---

### Task 5: JobScout Agent

**Files:**
- Create: `backend/agents/job_scout.py`
- Create: `backend/tests/test_job_scout_agent.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_job_scout_agent.py
import json
import pytest
from unittest.mock import patch, MagicMock

PREFERENCES = {
    "job_titles": ["Python Engineer"],
    "location": "Remote",
    "remote_hybrid": "remote",
    "experience_level": "senior",
    "domain": "backend",
    "company_size": ["startup"],
}

MOCK_SERP_RESULTS = [
    {
        "title": "Senior Python Engineer",
        "company": "Acme",
        "location": "Remote",
        "description": "Build APIs",
        "url": "https://acme.com/jobs/1",
    }
]


def _tool_use_response(tool_id, tool_input):
    block = MagicMock()
    block.type = "tool_use"
    block.name = "search_jobs"
    block.id = tool_id
    block.input = tool_input
    resp = MagicMock()
    resp.stop_reason = "tool_use"
    resp.content = [block]
    return resp


def _end_turn_response(scored_jobs):
    block = MagicMock()
    block.type = "text"
    block.text = json.dumps(scored_jobs)
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    resp.content = [block]
    return resp


def test_run_job_scout_returns_scored_jobs():
    scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.9}]
    with patch("backend.agents.job_scout.anthropic.Anthropic") as MockClient, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS):
        client = MagicMock()
        MockClient.return_value = client
        client.messages.create.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer", "location": "Remote"}),
            _end_turn_response(scored),
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert len(result) == 1
    assert result[0]["match_score"] == 0.9


def test_run_job_scout_filters_below_threshold():
    low_scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.3}]
    with patch("backend.agents.job_scout.anthropic.Anthropic") as MockClient, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS), \
         patch("backend.agents.job_scout.settings") as mock_settings:
        mock_settings.SCOUT_MODEL = "claude-haiku-4-5"
        mock_settings.ANTHROPIC_API_KEY = "test"
        mock_settings.JOB_MATCH_THRESHOLD = 0.6
        client = MagicMock()
        MockClient.return_value = client
        client.messages.create.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer", "location": "Remote"}),
            _end_turn_response(low_scored),
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert result == []


def test_run_job_scout_handles_malformed_response():
    """Agent returns non-JSON text — should return empty list gracefully."""
    with patch("backend.agents.job_scout.anthropic.Anthropic") as MockClient, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS):
        client = MagicMock()
        MockClient.return_value = client
        block = MagicMock()
        block.type = "text"
        block.text = "Sorry, I could not find any jobs."
        resp = MagicMock()
        resp.stop_reason = "end_turn"
        resp.content = [block]
        client.messages.create.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer"}),
            resp,
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert result == []
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend && pytest tests/test_job_scout_agent.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `backend/agents/job_scout.py`**

```python
import json
import anthropic
from backend.config import settings
from backend.tools.serp import search_jobs

TOOLS = [
    {
        "name": "search_jobs",
        "description": "Search for job listings using SerpAPI Google Jobs. Call once per job title.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Job title + keywords, e.g. 'Senior Python Engineer remote'"
                },
                "location": {
                    "type": "string",
                    "description": "Location filter, e.g. 'Remote' or 'New York, NY'"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to fetch (max 20)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    }
]

SYSTEM_PROMPT = """You are a job search assistant.
1. Use search_jobs to find jobs for each job title in the user's preferences.
2. Score each result 0.0–1.0 based on how well it matches the criteria.
3. Return ONLY a valid JSON array. No other text.

Scoring weights: title match (high), remote/location match (high), experience level (medium), domain (medium), company size (low).

Output format:
[{"title": "...", "company": "...", "location": "...", "description": "...", "url": "...", "match_score": 0.85}]"""


def _execute_tool(name: str, tool_input: dict) -> str:
    if name == "search_jobs":
        results = search_jobs(
            query=tool_input["query"],
            location=tool_input.get("location", ""),
            num_results=tool_input.get("num_results", 10),
        )
        return json.dumps(results)
    raise ValueError(f"Unknown tool: {name}")


def run_job_scout(preferences: dict) -> list[dict]:
    """Run the JobScout agentic loop. Returns jobs scoring >= JOB_MATCH_THRESHOLD."""
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    messages = [
        {
            "role": "user",
            "content": f"Find and score jobs for these preferences:\n{json.dumps(preferences, indent=2)}\n\nSearch each job title. Return a JSON array of scored jobs.",
        }
    ]

    while True:
        response = client.messages.create(
            model=settings.SCOUT_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    try:
                        jobs = json.loads(block.text)
                        return [j for j in jobs if j.get("match_score", 0) >= settings.JOB_MATCH_THRESHOLD]
                    except (json.JSONDecodeError, TypeError):
                        return []
            return []

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if getattr(block, "type", None) == "tool_use":
                    result = _execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd backend && pytest tests/test_job_scout_agent.py -v
```

Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/agents/job_scout.py backend/tests/test_job_scout_agent.py
git commit -m "feat: add JobScout agent with Anthropic tool-use agentic loop"
```

---

### Task 6: Preferences Router

**Files:**
- Create: `backend/routers/preferences.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_preferences_router.py`

- [ ] **Step 1: Create `backend/tests/conftest.py`**

```python
# backend/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.database import Base, get_db


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    with Session(db_engine) as session:
        yield session


@pytest.fixture(scope="function")
def client(db_engine):
    # Import here to avoid circular issues before app is assembled
    from backend.main import app

    def override_get_db():
        with Session(db_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Write failing tests**

```python
# backend/tests/test_preferences_router.py
def test_get_preferences_empty(client):
    response = client.get("/preferences")
    assert response.status_code == 200
    assert response.json() is None


def test_post_preferences(client):
    payload = {
        "job_titles": ["Python Engineer", "Backend Engineer"],
        "location": "Remote",
        "remote_hybrid": "remote",
        "experience_level": "senior",
        "domain": "backend",
        "company_size": ["startup"],
        "poll_interval_hrs": 4,
    }
    response = client.post("/preferences", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["location"] == "Remote"
    assert data["poll_interval_hrs"] == 4
    assert data["job_titles"] == ["Python Engineer", "Backend Engineer"]


def test_post_preferences_updates_existing(client):
    client.post("/preferences", json={"job_titles": ["Python Eng"], "location": "NYC", "remote_hybrid": "hybrid"})
    client.post("/preferences", json={"job_titles": ["Data Eng"], "location": "Remote", "remote_hybrid": "remote"})
    response = client.get("/preferences")
    assert response.status_code == 200
    assert response.json()["location"] == "Remote"
    # Exactly one record
    assert response.json()["job_titles"] == ["Data Eng"]
```

- [ ] **Step 3: Run tests — expect failure**

```bash
cd backend && pytest tests/test_preferences_router.py -v
```

Expected: import error (main.py doesn't exist yet — that's OK, create a stub)

- [ ] **Step 4: Create stub `backend/main.py` (full version in Task 10)**

```python
from fastapi import FastAPI
from backend.database import get_db
from backend.routers import preferences, resume, jobs

app = FastAPI(title="JobApplierAgent")
app.include_router(preferences.router)
app.include_router(resume.router)
app.include_router(jobs.router)

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Implement `backend/routers/preferences.py`**

```python
import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Preference

router = APIRouter()


class PreferenceRequest(BaseModel):
    job_titles: list[str]
    location: str = ""
    remote_hybrid: str = "any"
    experience_level: str = ""
    domain: str = ""
    company_size: list[str] = []
    poll_interval_hrs: int = 6


class PreferenceResponse(BaseModel):
    id: int
    job_titles: list[str]
    location: str
    remote_hybrid: str
    experience_level: str
    domain: str
    company_size: list[str]
    poll_interval_hrs: int

    class Config:
        from_attributes = True


def _deserialize(pref: Preference) -> Preference:
    pref.job_titles = json.loads(pref.job_titles)
    pref.company_size = json.loads(pref.company_size or "[]")
    return pref


@router.get("/preferences", response_model=PreferenceResponse | None)
def get_preferences(db: Session = Depends(get_db)):
    pref = db.query(Preference).first()
    return _deserialize(pref) if pref else None


@router.post("/preferences", response_model=PreferenceResponse)
def save_preferences(body: PreferenceRequest, db: Session = Depends(get_db)):
    pref = db.query(Preference).first() or Preference()
    pref.job_titles = json.dumps(body.job_titles)
    pref.location = body.location
    pref.remote_hybrid = body.remote_hybrid
    pref.experience_level = body.experience_level
    pref.domain = body.domain
    pref.company_size = json.dumps(body.company_size)
    pref.poll_interval_hrs = body.poll_interval_hrs
    db.add(pref)
    db.commit()
    db.refresh(pref)
    return _deserialize(pref)
```

- [ ] **Step 6: Run tests — expect pass**

```bash
cd backend && pytest tests/test_preferences_router.py -v
```

Expected: 3 tests PASSED

- [ ] **Step 7: Commit**

```bash
git add backend/main.py backend/routers/preferences.py backend/tests/conftest.py backend/tests/test_preferences_router.py
git commit -m "feat: add preferences API router"
```

---

### Task 7: Resume Router

**Files:**
- Create: `backend/routers/resume.py`
- Create: `backend/tests/test_resume_router.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_resume_router.py
import io


def test_upload_resume(client, tmp_path, monkeypatch):
    monkeypatch.setattr("backend.routers.resume.settings.UPLOAD_DIR", str(tmp_path))
    response = client.post(
        "/resume",
        files={"file": ("my_resume.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "my_resume.pdf"
    assert "filepath" in data


def test_get_resume_returns_latest(client, tmp_path, monkeypatch):
    monkeypatch.setattr("backend.routers.resume.settings.UPLOAD_DIR", str(tmp_path))
    for name in ["v1.pdf", "v2.pdf"]:
        client.post("/resume", files={"file": (name, io.BytesIO(b"content"), "application/pdf")})
    response = client.get("/resume")
    assert response.status_code == 200
    assert response.json()["filename"] == "v2.pdf"


def test_get_resume_empty(client):
    response = client.get("/resume")
    assert response.status_code == 200
    assert response.json() is None
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend && pytest tests/test_resume_router.py -v
```

Expected: 404 on all

- [ ] **Step 3: Implement `backend/routers/resume.py`**

```python
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.config import settings
from backend.database import get_db
from backend.models import Resume

router = APIRouter()


class ResumeResponse(BaseModel):
    id: int
    filename: str
    filepath: str

    class Config:
        from_attributes = True


@router.post("/resume", response_model=ResumeResponse)
def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filepath = upload_dir / file.filename
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    existing = db.query(Resume).first()
    if existing:
        db.delete(existing)
        db.commit()
    resume = Resume(filename=file.filename, filepath=str(filepath))
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("/resume", response_model=ResumeResponse | None)
def get_resume(db: Session = Depends(get_db)):
    return db.query(Resume).first()
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd backend && pytest tests/test_resume_router.py -v
```

Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/routers/resume.py backend/tests/test_resume_router.py
git commit -m "feat: add resume upload router"
```

---

### Task 8: Jobs Router

**Files:**
- Create: `backend/routers/jobs.py`
- Create: `backend/tests/test_jobs_router.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_jobs_router.py
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
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend && pytest tests/test_jobs_router.py -v
```

Expected: 404 on most

- [ ] **Step 3: Implement `backend/routers/jobs.py`**

```python
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Job
from backend.scheduler import run_poll

router = APIRouter()


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    url: str
    description: Optional[str]
    location: Optional[str]
    match_score: Optional[float]
    source: str
    status: str
    error_reason: Optional[str]

    class Config:
        from_attributes = True


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).all()


# IMPORTANT: /jobs/refresh MUST be declared before /jobs/{job_id} to prevent
# FastAPI from matching the literal string "refresh" as a job_id parameter.
@router.post("/jobs/refresh")
def refresh_jobs():
    """Manually trigger a job discovery poll."""
    run_poll()
    return {"status": "poll triggered"}


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/jobs/{job_id}", response_model=JobResponse)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return job
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd backend && pytest tests/test_jobs_router.py -v
```

Expected: 5 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/routers/jobs.py backend/tests/test_jobs_router.py
git commit -m "feat: add jobs router with list, detail, delete, and refresh endpoints"
```

---

### Task 9: Scheduler

**Files:**
- Create: `backend/scheduler.py`
- Create: `backend/tests/test_scheduler.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_scheduler.py
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
         patch("backend.scheduler.SessionLocal", return_value=db_session):
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
         patch("backend.scheduler.SessionLocal", return_value=db_session):
        from backend.scheduler import run_poll
        run_poll()
    assert db_session.query(Job).count() == 1
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend && pytest tests/test_scheduler.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `backend/scheduler.py`**

```python
import json
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.exc import IntegrityError
from backend.database import SessionLocal
from backend.models import Preference, Job
from backend.agents.job_scout import run_job_scout

logger = logging.getLogger(__name__)


def get_preferences_dict() -> dict | None:
    db = SessionLocal()
    try:
        pref = db.query(Preference).first()
        if not pref:
            return None
        return {
            "job_titles": json.loads(pref.job_titles),
            "location": pref.location or "",
            "remote_hybrid": pref.remote_hybrid or "any",
            "experience_level": pref.experience_level or "",
            "domain": pref.domain or "",
            "company_size": json.loads(pref.company_size or "[]"),
        }
    finally:
        db.close()


def run_poll():
    """One job discovery poll. Called on startup and by scheduler."""
    preferences = get_preferences_dict()
    if not preferences:
        logger.info("No preferences configured — skipping job poll")
        return

    logger.info("Running job scout poll...")
    try:
        jobs = run_job_scout(preferences)
    except Exception as e:
        logger.error(f"Job scout failed: {e}")
        return

    db = SessionLocal()
    try:
        inserted = 0
        for job_data in jobs:
            job = Job(
                title=job_data["title"],
                company=job_data["company"],
                url=job_data["url"],
                description=job_data.get("description", ""),
                location=job_data.get("location", ""),
                match_score=job_data.get("match_score", 0.0),
                source="serpapi",
                status="new",
            )
            db.add(job)
            try:
                db.commit()
                inserted += 1
            except IntegrityError:
                db.rollback()  # duplicate URL — skip silently
        logger.info(f"Poll complete: {inserted} new jobs")
    finally:
        db.close()


def start_scheduler(poll_interval_hrs: int = 6):
    """Start background scheduler and run an immediate poll on startup."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_poll, "interval", hours=poll_interval_hrs)
    scheduler.start()
    run_poll()  # immediate poll on startup — no waiting for first interval
    return scheduler
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd backend && pytest tests/test_scheduler.py -v
```

Expected: 4 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/scheduler.py backend/tests/test_scheduler.py
git commit -m "feat: add APScheduler with immediate startup poll and deduplication"
```

---

### Task 10: FastAPI App Assembly

**Files:**
- Modify: `backend/main.py` (replace stub with full version)
- Create: `backend/tests/test_main.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_main.py
from unittest.mock import patch


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_all_routes_registered(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/preferences" in paths
    assert "/resume" in paths
    assert "/jobs" in paths
    assert "/jobs/{job_id}" in paths
    assert "/jobs/refresh" in paths
```

- [ ] **Step 2: Run tests — expect pass with stub (health only fails if stub is missing)**

```bash
cd backend && pytest tests/test_main.py -v
```

- [ ] **Step 3: Replace stub `backend/main.py` with full version**

```python
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base, get_db
from backend.routers import preferences, resume, jobs
from backend.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    global _scheduler
    _scheduler = start_scheduler(poll_interval_hrs=6)
    yield
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()


app = FastAPI(title="JobApplierAgent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(preferences.router)
app.include_router(resume.router)
app.include_router(jobs.router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Run full backend test suite**

```bash
cd backend && pytest -v
```

Expected: All tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/tests/test_main.py
git commit -m "feat: assemble FastAPI app with lifespan, CORS, and scheduler"
```

---

### Task 11: Frontend Scaffold

**Files:**
- Create: `frontend/` (Vite + React)

- [ ] **Step 1: Scaffold Vite project**

```bash
npm create vite@latest frontend -- --template react
cd frontend && npm install
```

- [ ] **Step 2: Install additional dependencies**

```bash
cd frontend
npm install axios react-router-dom
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

- [ ] **Step 3: Replace `frontend/vite.config.js`**

Note: The proxy uses a regex catch-all that covers all API paths added across all 4 phases (`/preferences`, `/resume`, `/jobs`, `/applications`, `/outreach`, `/auth`, `/webhook`, `/health`). This avoids having to update the proxy in every phase.

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '^/(preferences|resume|jobs|applications|outreach|auth|webhook|health)': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.js'],
  },
})
```

- [ ] **Step 4: Create `frontend/src/test-setup.js`**

```javascript
import '@testing-library/jest-dom'
```

- [ ] **Step 5: Add test script to `frontend/package.json`**

Add under `"scripts"`:
```json
"test": "vitest",
"test:run": "vitest run"
```

- [ ] **Step 6: Run tests — expect no test files found**

```bash
cd frontend && npm run test:run
```

Expected: `No test files found`

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "chore: scaffold React + Vite frontend with Vitest"
```

---

### Task 12: API Client

**Files:**
- Create: `frontend/src/api/client.js`
- Create: `frontend/src/api/client.test.js`

- [ ] **Step 1: Write failing tests**

```javascript
// frontend/src/api/client.test.js
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('axios')

describe('API client', () => {
  let axios

  beforeEach(async () => {
    vi.resetModules()
    axios = (await import('axios')).default
  })

  it('getJobs calls GET /jobs', async () => {
    axios.get = vi.fn().mockResolvedValue({ data: [] })
    const { getJobs } = await import('./client.js')
    await getJobs()
    expect(axios.get).toHaveBeenCalledWith('/jobs')
  })

  it('savePreferences calls POST /preferences', async () => {
    axios.post = vi.fn().mockResolvedValue({ data: {} })
    const { savePreferences } = await import('./client.js')
    const prefs = { job_titles: ['Engineer'], location: 'Remote' }
    await savePreferences(prefs)
    expect(axios.post).toHaveBeenCalledWith('/preferences', prefs)
  })

  it('deleteJob calls DELETE /jobs/:id', async () => {
    axios.delete = vi.fn().mockResolvedValue({ data: {} })
    const { deleteJob } = await import('./client.js')
    await deleteJob(42)
    expect(axios.delete).toHaveBeenCalledWith('/jobs/42')
  })
})
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd frontend && npm run test:run
```

Expected: `Cannot find module './client.js'`

- [ ] **Step 3: Implement `frontend/src/api/client.js`**

```javascript
import axios from 'axios'

export const getJobs = () => axios.get('/jobs').then(r => r.data)
export const getJob = (id) => axios.get(`/jobs/${id}`).then(r => r.data)
export const deleteJob = (id) => axios.delete(`/jobs/${id}`).then(r => r.data)
export const refreshJobs = () => axios.post('/jobs/refresh').then(r => r.data)
export const getPreferences = () => axios.get('/preferences').then(r => r.data)
export const savePreferences = (data) => axios.post('/preferences', data).then(r => r.data)
export const getResume = () => axios.get('/resume').then(r => r.data)
export const uploadResume = (file) => {
  const form = new FormData()
  form.append('file', file)
  return axios.post('/resume', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd frontend && npm run test:run
```

Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/
git commit -m "feat: add typed API client"
```

---

### Task 13: StatusBadge and JobCard Components

**Files:**
- Create: `frontend/src/components/StatusBadge.jsx`
- Create: `frontend/src/components/JobCard.jsx`
- Create: `frontend/src/components/StatusBadge.test.jsx`
- Create: `frontend/src/components/JobCard.test.jsx`

- [ ] **Step 1: Write failing tests**

```jsx
// frontend/src/components/StatusBadge.test.jsx
import { render, screen } from '@testing-library/react'
import { StatusBadge } from './StatusBadge'

test('renders status text', () => {
  render(<StatusBadge status="new" />)
  expect(screen.getByText('new')).toBeInTheDocument()
})

test('renders match score as percentage', () => {
  render(<StatusBadge score={0.85} />)
  expect(screen.getByText('85%')).toBeInTheDocument()
})
```

```jsx
// frontend/src/components/JobCard.test.jsx
import { render, screen, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import { JobCard } from './JobCard'

const job = {
  id: 1, title: 'Senior Python Engineer', company: 'Acme Corp',
  location: 'Remote', match_score: 0.9, status: 'new',
  description: 'Build cool APIs with Python', url: 'https://acme.com/1', source: 'serpapi',
}

test('renders title and company', () => {
  render(<JobCard job={job} />)
  expect(screen.getByText('Senior Python Engineer')).toBeInTheDocument()
  expect(screen.getByText('Acme Corp')).toBeInTheDocument()
})

test('calls onDelete when dismiss clicked', () => {
  const onDelete = vi.fn()
  render(<JobCard job={job} onDelete={onDelete} />)
  fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
  expect(onDelete).toHaveBeenCalledWith(1)
})

test('shows webhook badge for webhook source', () => {
  render(<JobCard job={{ ...job, source: 'webhook' }} />)
  expect(screen.getByText(/webhook/i)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd frontend && npm run test:run
```

Expected: `Cannot find module`

- [ ] **Step 3: Implement `frontend/src/components/StatusBadge.jsx`**

```jsx
const STATUS_COLORS = {
  new: '#3b82f6', saved: '#8b5cf6', dismissed: '#6b7280',
  applying: '#f59e0b', applied: '#22c55e', error: '#ef4444',
  emailing: '#f59e0b', emailed: '#22c55e',
}

export function StatusBadge({ status, score }) {
  const style = { color: '#fff', padding: '2px 8px', borderRadius: 4, fontSize: 12 }
  if (score !== undefined) {
    const pct = Math.round(score * 100)
    const bg = pct >= 80 ? '#22c55e' : pct >= 60 ? '#f59e0b' : '#ef4444'
    return <span style={{ ...style, background: bg }}>{pct}%</span>
  }
  return <span style={{ ...style, background: STATUS_COLORS[status] || '#6b7280' }}>{status}</span>
}
```

- [ ] **Step 4: Implement `frontend/src/components/JobCard.jsx`**

```jsx
import { StatusBadge } from './StatusBadge'

export function JobCard({ job, onDelete }) {
  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
        <div>
          <h3 style={{ margin: 0 }}>{job.title}</h3>
          <p style={{ margin: '4px 0', color: '#6b7280' }}>{job.company} · {job.location}</p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <StatusBadge score={job.match_score} />
          <StatusBadge status={job.status} />
          {job.source === 'webhook' && (
            <span style={{ fontSize: 11, color: '#8b5cf6' }}>via webhook</span>
          )}
        </div>
      </div>
      <p style={{ fontSize: 14, color: '#374151', marginTop: 8 }}>
        {job.description?.slice(0, 200)}{job.description?.length > 200 ? '…' : ''}
      </p>
      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <a href={job.url} target="_blank" rel="noopener noreferrer">
          <button>View Job</button>
        </a>
        <button disabled title="Available in Phase 2">Apply</button>
        <button disabled title="Available in Phase 3">Email HR</button>
        <button onClick={() => onDelete?.(job.id)} aria-label="Dismiss">Dismiss</button>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Run tests — expect pass**

```bash
cd frontend && npm run test:run
```

Expected: 5 tests PASSED

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/
git commit -m "feat: add StatusBadge and JobCard components"
```

---

### Task 14: Dashboard and Preferences Pages

**Files:**
- Create: `frontend/src/pages/Dashboard.jsx`
- Create: `frontend/src/pages/Preferences.jsx`
- Create: `frontend/src/pages/Dashboard.test.jsx`
- Create: `frontend/src/pages/Preferences.test.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/main.jsx`

- [ ] **Step 1: Write failing page tests**

```jsx
// frontend/src/pages/Dashboard.test.jsx
import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import * as api from '../api/client'
import { Dashboard } from './Dashboard'

const mockJobs = [{
  id: 1, title: 'Python Engineer', company: 'Acme', location: 'Remote',
  match_score: 0.9, status: 'new', description: 'Build APIs', url: 'https://acme.com/1', source: 'serpapi',
}]

test('renders job cards from API', async () => {
  vi.spyOn(api, 'getJobs').mockResolvedValue(mockJobs)
  render(<Dashboard />)
  await waitFor(() => expect(screen.getByText('Python Engineer')).toBeInTheDocument())
})

test('shows empty state when no jobs', async () => {
  vi.spyOn(api, 'getJobs').mockResolvedValue([])
  render(<Dashboard />)
  await waitFor(() => expect(screen.getByText(/no jobs found/i)).toBeInTheDocument())
})
```

```jsx
// frontend/src/pages/Preferences.test.jsx
import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import * as api from '../api/client'
import { Preferences } from './Preferences'

test('renders the preferences form', async () => {
  vi.spyOn(api, 'getPreferences').mockResolvedValue(null)
  vi.spyOn(api, 'getResume').mockResolvedValue(null)
  render(<Preferences />)
  await waitFor(() => expect(screen.getByLabelText(/job titles/i)).toBeInTheDocument())
})
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd frontend && npm run test:run
```

Expected: `Cannot find module`

- [ ] **Step 3: Implement `frontend/src/pages/Dashboard.jsx`**

```jsx
import { useEffect, useState } from 'react'
import { getJobs, deleteJob, refreshJobs } from '../api/client'
import { JobCard } from '../components/JobCard'

export function Dashboard() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    getJobs().then(setJobs).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleDelete = (id) => {
    deleteJob(id).then(() => setJobs(js => js.filter(j => j.id !== id)))
  }

  const handleRefresh = () => {
    refreshJobs().then(load)
  }

  if (loading) return <p>Loading jobs...</p>

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Job Dashboard</h1>
        <button onClick={handleRefresh}>Refresh Now</button>
      </div>
      {jobs.length === 0
        ? <p>No jobs found. Configure your preferences and refresh to discover jobs.</p>
        : jobs.map(job => <JobCard key={job.id} job={job} onDelete={handleDelete} />)
      }
    </div>
  )
}
```

- [ ] **Step 4: Implement `frontend/src/pages/Preferences.jsx`**

```jsx
import { useEffect, useState } from 'react'
import { getPreferences, savePreferences, uploadResume, getResume } from '../api/client'

export function Preferences() {
  const [form, setForm] = useState({
    job_titles: '', location: '', remote_hybrid: 'any',
    experience_level: '', domain: '', company_size: '', poll_interval_hrs: 6,
  })
  const [resume, setResume] = useState(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getPreferences().then(pref => {
      if (pref) setForm({
        job_titles: pref.job_titles.join(', '),
        location: pref.location || '',
        remote_hybrid: pref.remote_hybrid || 'any',
        experience_level: pref.experience_level || '',
        domain: pref.domain || '',
        company_size: (pref.company_size || []).join(', '),
        poll_interval_hrs: pref.poll_interval_hrs || 6,
      })
    })
    getResume().then(setResume)
  }, [])

  const set = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }))

  const handleSave = (e) => {
    e.preventDefault()
    savePreferences({
      ...form,
      job_titles: form.job_titles.split(',').map(s => s.trim()).filter(Boolean),
      company_size: form.company_size.split(',').map(s => s.trim()).filter(Boolean),
      poll_interval_hrs: Number(form.poll_interval_hrs),
    }).then(() => setSaved(true))
  }

  const handleResumeUpload = (e) => {
    const file = e.target.files[0]
    if (file) uploadResume(file).then(setResume)
  }

  return (
    <div>
      <h1>Preferences</h1>
      <form onSubmit={handleSave}>
        <div><label htmlFor="job_titles">Job Titles (comma-separated)</label>
          <input id="job_titles" value={form.job_titles} onChange={set('job_titles')} /></div>
        <div><label htmlFor="location">Location</label>
          <input id="location" value={form.location} onChange={set('location')} /></div>
        <div><label htmlFor="remote_hybrid">Work Arrangement</label>
          <select id="remote_hybrid" value={form.remote_hybrid} onChange={set('remote_hybrid')}>
            <option value="any">Any</option><option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option><option value="onsite">Onsite</option>
          </select></div>
        <div><label htmlFor="experience_level">Experience Level</label>
          <input id="experience_level" value={form.experience_level} onChange={set('experience_level')} /></div>
        <div><label htmlFor="domain">Domain</label>
          <input id="domain" value={form.domain} onChange={set('domain')} /></div>
        <div><label htmlFor="company_size">Company Size (comma-separated)</label>
          <input id="company_size" value={form.company_size} onChange={set('company_size')} /></div>
        <div><label htmlFor="poll_interval_hrs">Poll Interval (hours)</label>
          <input id="poll_interval_hrs" type="number" min="1" value={form.poll_interval_hrs} onChange={set('poll_interval_hrs')} /></div>
        <button type="submit">Save Preferences</button>
        {saved && <span style={{ color: 'green', marginLeft: 8 }}>Saved!</span>}
      </form>
      <h2>Resume</h2>
      {resume && <p>Current: <strong>{resume.filename}</strong></p>}
      <input type="file" accept=".pdf,.docx" onChange={handleResumeUpload} />
    </div>
  )
}
```

- [ ] **Step 5: Update `frontend/src/App.jsx`**

```jsx
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { Preferences } from './pages/Preferences'

export default function App() {
  return (
    <BrowserRouter>
      <nav style={{ padding: '12px 24px', borderBottom: '1px solid #e5e7eb', display: 'flex', gap: 16 }}>
        <Link to="/">Dashboard</Link>
        <Link to="/preferences">Preferences</Link>
      </nav>
      <main style={{ padding: 24 }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/preferences" element={<Preferences />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
```

- [ ] **Step 6: Update `frontend/src/main.jsx`**

```jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

- [ ] **Step 7: Run all frontend tests**

```bash
cd frontend && npm run test:run
```

Expected: All tests PASSED

- [ ] **Step 8: Run full backend test suite**

```bash
cd backend && pytest -v
```

Expected: All tests PASSED

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/ frontend/src/App.jsx frontend/src/main.jsx
git commit -m "feat: add Dashboard and Preferences pages"
```

---

## Final Smoke Test

- [ ] **Start backend**

```bash
cd backend && uvicorn main:app --reload --port 8000
```

Expected: Server starts. Logs show scheduler started and one poll triggered. If no preferences configured: `No preferences configured — skipping job poll`.

- [ ] **Start frontend**

```bash
cd frontend && npm run dev
```

Expected: Vite dev server at `http://localhost:5173`

- [ ] **Manual smoke test**

1. Open `http://localhost:5173/preferences`
2. Fill in job titles and criteria, click Save — see "Saved!"
3. Upload a PDF resume — see filename appear
4. Navigate to `/` — see Dashboard with "Refresh Now" button
5. Click "Refresh Now" — triggers poll (may populate jobs if `SERP_API_KEY` is configured)

- [ ] **Final commit**

```bash
git add .
git commit -m "feat: phase 1 complete — foundation and job discovery dashboard"
```
