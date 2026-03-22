# Phase 2: Supervised Application Flow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add supervised application automation — Applicator Agent scrapes career site forms with Playwright, tailors the resume via AI, pre-fills fields for user review, then opens a browser for the user to submit manually.

**Architecture:** `Applicator Agent` uses the Anthropic tool-use loop with two tools: `fetch_application_form` (Playwright scrapes visible fields) and `tailor_resume` (Haiku rewrites resume text for the role). The backend returns a prefilled payload + tailored resume text to the frontend. The user reviews, edits if needed, then clicks "Open in Browser" which launches Playwright with pre-filled fields. Application status is tracked in the `applications` table with `jobs.status` updated in tandem.

**Tech Stack:** Python 3.12, FastAPI, Playwright (sync), anthropic SDK, pdfminer.six or python-docx (resume parsing), pytest, React 18, Vitest, @testing-library/react

**Prerequisites:** Phase 1 complete. `backend/`, `frontend/`, SQLite DB with `jobs` table in place.

**Spec:** `docs/superpowers/specs/2026-03-22-job-applier-agent-design.md` (Phase 2 section)

---

## File Map

| File | Responsibility |
|---|---|
| `backend/tools/resume_tools.py` | `tailor_resume(job_description, master_resume_path, output_format, output_path)` — shared by Applicator and Outreach agents |
| `backend/tools/playwright_tools.py` | `fetch_application_form(url)` — Playwright scrapes form fields; `open_prefilled_form(url, payload)` — opens browser with pre-filled fields |
| `backend/agents/applicator.py` | `run_applicator(job_id, job_url, job_description, resume_path)` — agentic loop; returns `ApplicationResult` |
| `backend/routers/applications.py` | `POST /applications`, `GET /applications`, `PATCH /applications/{id}` |
| `backend/models.py` | Add `Application` model (modify existing file) |
| `backend/tests/test_resume_tools.py` | Unit tests for `tailor_resume` |
| `backend/tests/test_playwright_tools.py` | Unit tests for form scraping with mocked Playwright |
| `backend/tests/test_applicator_agent.py` | Unit tests for applicator agentic loop |
| `backend/tests/test_applications_router.py` | API tests for applications routes |
| `frontend/src/api/client.js` | Add: `triggerApply`, `getApplications`, `updateApplication`, `openInBrowser` |
| `frontend/src/components/ReviewPanel.jsx` | Resume diff + form fields preview + Open in Browser button |
| `frontend/src/components/ReviewPanel.test.jsx` | Component tests |
| `frontend/src/pages/Applications.jsx` | Pipeline view: Discovered → Reviewing → Applied → Response |
| `frontend/src/pages/Applications.test.jsx` | Page tests |
| `frontend/src/App.jsx` | Add `/applications` route |

---

## Tasks

---

### Task 1: Resume Tailoring Tool

**Files:**
- Create: `backend/tools/resume_tools.py`
- Create: `backend/tests/test_resume_tools.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_resume_tools.py
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture
def sample_resume(tmp_path):
    """Write a plain-text .txt file as a stand-in for resume parsing."""
    f = tmp_path / "resume.txt"
    f.write_text("John Doe\nSenior Python Engineer\nExperience: FastAPI, PostgreSQL, Docker")
    return str(f)


def test_tailor_resume_text_returns_string(sample_resume):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Tailored resume text for Python role")]
    with patch("backend.tools.resume_tools.anthropic.Anthropic") as MockClient:
        client = MagicMock()
        MockClient.return_value = client
        client.messages.create.return_value = mock_response
        from backend.tools.resume_tools import tailor_resume
        result = tailor_resume(
            job_description="Senior Python Engineer at Acme",
            master_resume_path=sample_resume,
            output_format="text",
            output_path="",
        )
    assert isinstance(result, str)
    assert "Tailored" in result


def test_tailor_resume_pdf_writes_file(sample_resume, tmp_path):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Tailored resume content")]
    output_path = str(tmp_path / "tailored.pdf")
    with patch("backend.tools.resume_tools.anthropic.Anthropic") as MockClient, \
         patch("backend.tools.resume_tools._write_pdf") as mock_pdf:
        client = MagicMock()
        MockClient.return_value = client
        client.messages.create.return_value = mock_response
        from backend.tools.resume_tools import tailor_resume
        result = tailor_resume(
            job_description="Senior Python Engineer at Acme",
            master_resume_path=sample_resume,
            output_format="pdf",
            output_path=output_path,
        )
    assert result == output_path
    mock_pdf.assert_called_once_with("Tailored resume content", output_path)


def test_tailor_resume_reads_resume_content(sample_resume):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="output")]
    with patch("backend.tools.resume_tools.anthropic.Anthropic") as MockClient:
        client = MagicMock()
        MockClient.return_value = client
        client.messages.create.return_value = mock_response
        from backend.tools.resume_tools import tailor_resume, _read_resume
        content = _read_resume(sample_resume)
        assert "Senior Python Engineer" in content
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend && pytest tests/test_resume_tools.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Install resume parsing and PDF writing dependencies**

```bash
cd backend && pip install fpdf2 pdfminer.six python-docx
echo "fpdf2==2.7.9" >> requirements.txt
echo "pdfminer.six==20231228" >> requirements.txt
echo "python-docx==1.1.2" >> requirements.txt
```

- [ ] **Step 4: Implement `backend/tools/resume_tools.py`**

```python
import anthropic
from pathlib import Path
from typing import Literal
from fpdf import FPDF
from backend.config import settings


def _read_resume(filepath: str) -> str:
    """Read resume file content as plain text. Supports .txt, .pdf, .docx."""
    path = Path(filepath)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pdfminer.high_level import extract_text
        return extract_text(str(path))
    elif suffix in (".docx", ".doc"):
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        return path.read_text(errors="ignore")


def _write_pdf(text: str, output_path: str) -> None:
    """Write plain text as a simple PDF file."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in text.split("\n"):
        pdf.multi_cell(0, 6, line)
    pdf.output(output_path)


TAILOR_SYSTEM = """You are a professional resume writer. Given a job description and a master resume,
rewrite the resume to highlight the most relevant experience and skills for this specific role.
Keep it truthful — do not invent experience. Return ONLY the tailored resume text, no commentary."""


def tailor_resume(
    job_description: str,
    master_resume_path: str,
    output_format: Literal["text", "pdf"],
    output_path: str,
) -> str:
    """
    Tailor the master resume for a specific job.

    output_format="text": returns tailored resume as a plain text string (output_path ignored)
    output_format="pdf": writes PDF to output_path and returns output_path
    """
    resume_content = _read_resume(master_resume_path)
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=settings.APPLICATOR_MODEL,
        max_tokens=2048,
        system=TAILOR_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Job Description:\n{job_description}\n\nMaster Resume:\n{resume_content}\n\nTailor the resume for this role.",
            }
        ],
    )
    tailored_text = ""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            tailored_text = block.text
            break

    if output_format == "text":
        return tailored_text
    else:
        _write_pdf(tailored_text, output_path)
        return output_path
```

- [ ] **Step 5: Run tests — expect pass**

```bash
cd backend && pytest tests/test_resume_tools.py -v
```

Expected: 3 tests PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/tools/resume_tools.py backend/tests/test_resume_tools.py backend/requirements.txt
git commit -m "feat: add shared resume tailoring tool"
```

---

### Task 2: Playwright Tools

**Files:**
- Create: `backend/tools/playwright_tools.py`
- Create: `backend/tests/test_playwright_tools.py`

- [ ] **Step 1: Install Playwright**

```bash
cd backend && pip install playwright
playwright install chromium
echo "playwright>=1.48.0" >> requirements.txt
```

- [ ] **Step 2: Write failing tests**

```python
# backend/tests/test_playwright_tools.py
import pytest
from unittest.mock import patch, MagicMock


def make_mock_input(name, input_type="text", label="", placeholder=""):
    m = MagicMock()
    m.get_attribute.side_effect = lambda attr: {
        "name": name, "type": input_type, "id": name,
        "placeholder": placeholder,
    }.get(attr, "")
    return m


def test_fetch_application_form_returns_field_list():
    mock_page = MagicMock()
    mock_inputs = [
        make_mock_input("first_name"), make_mock_input("email", "email"),
        make_mock_input("resume", "file"),
    ]
    mock_page.query_selector_all.return_value = mock_inputs
    mock_page.title.return_value = "Apply at Acme"

    with patch("backend.tools.playwright_tools.sync_playwright") as mock_pw:
        mock_pw.return_value.__enter__.return_value.chromium.launch.return_value \
            .__enter__.return_value.new_page.return_value = mock_page
        from backend.tools.playwright_tools import fetch_application_form
        result = fetch_application_form("https://acme.com/apply")

    assert isinstance(result["fields"], list)
    assert any(f["name"] == "first_name" for f in result["fields"])
    # File inputs should be excluded from auto-fill
    assert not any(f["type"] == "file" for f in result["fields"])


def test_fetch_application_form_returns_manual_required_on_error():
    with patch("backend.tools.playwright_tools.sync_playwright") as mock_pw:
        mock_pw.return_value.__enter__.return_value.chromium.launch.side_effect = Exception("browser error")
        from backend.tools.playwright_tools import fetch_application_form
        result = fetch_application_form("https://acme.com/apply")
    assert result["status"] == "manual_required"
    assert result["url"] == "https://acme.com/apply"
```

- [ ] **Step 3: Run tests — expect failure**

```bash
cd backend && pytest tests/test_playwright_tools.py -v
```

Expected: `ImportError`

- [ ] **Step 4: Implement `backend/tools/playwright_tools.py`**

```python
import logging
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


def fetch_application_form(url: str) -> dict:
    """
    Launch a headless browser, navigate to the application URL, and scrape visible form fields.
    Returns {"fields": [...], "title": "..."} or {"status": "manual_required", "url": url} on failure.
    """
    try:
        with sync_playwright() as p:
            with p.chromium.launch(headless=True) as browser:
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=15000)
                inputs = page.query_selector_all("input, textarea, select")
                fields = []
                for el in inputs:
                    input_type = el.get_attribute("type") or "text"
                    if input_type in ("file", "hidden", "submit", "button"):
                        continue
                    fields.append({
                        "name": el.get_attribute("name") or el.get_attribute("id") or "",
                        "type": input_type,
                        "id": el.get_attribute("id") or "",
                        "placeholder": el.get_attribute("placeholder") or "",
                    })
                return {"fields": fields, "title": page.title(), "url": url}
    except Exception as e:
        logger.warning(f"Form scraping failed for {url}: {e}")
        return {"status": "manual_required", "url": url, "error": str(e)}


def open_prefilled_form(url: str, payload: dict) -> None:
    """
    Open a real (non-headless) browser window with form fields pre-filled.
    Control is handed to the user; this function returns immediately after filling.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=15000)
        for field_name, value in payload.items():
            try:
                locator = page.locator(f"[name='{field_name}'], [id='{field_name}']").first
                locator.fill(str(value))
            except Exception as e:
                logger.debug(f"Could not fill field {field_name}: {e}")
        # Leave browser open for user — do not close
        input("Press Enter in the terminal after you have submitted the form...")
        browser.close()
```

- [ ] **Step 5: Run tests — expect pass**

```bash
cd backend && pytest tests/test_playwright_tools.py -v
```

Expected: 2 tests PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/tools/playwright_tools.py backend/tests/test_playwright_tools.py backend/requirements.txt
git commit -m "feat: add Playwright form scraping and supervised prefill tools"
```

---

### Task 3: Application Model

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/tests/test_models.py`

- [ ] **Step 1: Write failing test**

```python
# Add to backend/tests/test_models.py
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
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd backend && pytest tests/test_models.py::test_create_application -v
```

Expected: `ImportError` on Application

- [ ] **Step 3: Add `Application` model to `backend/models.py`**

Append to the end of the file:

```python
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
```

- [ ] **Step 4: Run all model tests — expect pass**

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: All tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/models.py backend/tests/test_models.py
git commit -m "feat: add Application model"
```

---

### Task 4: Applicator Agent

**Files:**
- Create: `backend/agents/applicator.py`
- Create: `backend/tests/test_applicator_agent.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_applicator_agent.py
import json
import pytest
from unittest.mock import patch, MagicMock

MOCK_FORM = {
    "fields": [
        {"name": "first_name", "type": "text", "id": "first_name", "placeholder": ""},
        {"name": "email", "type": "email", "id": "email", "placeholder": ""},
    ],
    "url": "https://acme.com/apply",
}

MOCK_TAILORED = "John Doe\nSenior Python Engineer\nTailored for Acme role"


def _end_turn(text):
    block = MagicMock(type="text", text=text)
    resp = MagicMock(stop_reason="end_turn", content=[block])
    return resp


def test_run_applicator_returns_result():
    with patch("backend.agents.applicator.anthropic.Anthropic") as MockClient, \
         patch("backend.agents.applicator.fetch_application_form", return_value=MOCK_FORM), \
         patch("backend.agents.applicator.tailor_resume", return_value=MOCK_TAILORED):
        payload = json.dumps({"first_name": "John", "email": "john@example.com"})
        client = MagicMock()
        MockClient.return_value = client
        client.messages.create.return_value = _end_turn(payload)
        from backend.agents.applicator import run_applicator
        result = run_applicator(
            job_id=1,
            job_url="https://acme.com/apply",
            job_description="Senior Python Engineer",
            resume_path="uploads/resume.txt",
        )
    assert result["status"] == "ready"
    assert "form_payload" in result
    assert "tailored_resume" in result


def test_run_applicator_returns_manual_required_on_form_failure():
    with patch("backend.agents.applicator.fetch_application_form",
               return_value={"status": "manual_required", "url": "https://acme.com/apply"}), \
         patch("backend.agents.applicator.tailor_resume", return_value=MOCK_TAILORED):
        from backend.agents.applicator import run_applicator
        result = run_applicator(1, "https://acme.com/apply", "JD", "uploads/resume.txt")
    assert result["status"] == "manual_required"
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend && pytest tests/test_applicator_agent.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `backend/agents/applicator.py`**

```python
import json
import anthropic
from backend.config import settings
from backend.tools.playwright_tools import fetch_application_form
from backend.tools.resume_tools import tailor_resume

TOOLS = [
    {
        "name": "map_form_fields",
        "description": "Given scraped form fields and tailored resume text, map resume data to form field names. Return a JSON object of {field_name: value}.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fields": {"type": "array", "description": "List of form field descriptors"},
                "resume_text": {"type": "string", "description": "Tailored resume content"},
            },
            "required": ["fields", "resume_text"],
        },
    }
]

SYSTEM_PROMPT = """You are an application form assistant. Given form fields and a resume, produce a JSON mapping of {field_name: value} to pre-fill the form. Use only information from the resume. Return ONLY valid JSON."""


def run_applicator(job_id: int, job_url: str, job_description: str, resume_path: str) -> dict:
    """
    Run the Applicator agent.
    Returns:
      {"status": "ready", "form_payload": {...}, "tailored_resume": "..."}
      or {"status": "manual_required", "url": job_url}
    """
    # Step 1: scrape form
    form_result = fetch_application_form(job_url)
    if form_result.get("status") == "manual_required":
        return {"status": "manual_required", "url": job_url}

    # Step 2: tailor resume as text for form filling
    tailored = tailor_resume(
        job_description=job_description,
        master_resume_path=resume_path,
        output_format="text",
        output_path="",
    )

    # Step 3: map resume data to form fields
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=settings.APPLICATOR_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Form fields:\n{json.dumps(form_result['fields'], indent=2)}\n\nResume:\n{tailored}\n\nReturn a JSON object mapping field names to values.",
            }
        ],
    )

    payload = {}
    for block in response.content:
        if getattr(block, "type", None) == "text":
            try:
                payload = json.loads(block.text)
            except json.JSONDecodeError:
                payload = {}
            break

    return {
        "status": "ready",
        "form_payload": payload,
        "tailored_resume": tailored,
        "form_fields": form_result["fields"],
        "url": job_url,
    }
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd backend && pytest tests/test_applicator_agent.py -v
```

Expected: 2 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/agents/applicator.py backend/tests/test_applicator_agent.py
git commit -m "feat: add Applicator agent with form scraping and resume tailoring"
```

---

### Task 5: Applications Router

**Files:**
- Create: `backend/routers/applications.py`
- Create: `backend/tests/test_applications_router.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_applications_router.py
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
    # jobs.status should now be 'applying'
    db_session.refresh(job)
    assert job.status == "applying"


def test_get_applications(client, db_session, job):
    app = Application(job_id=job.id, status="pending")
    db_session.add(app)
    db_session.commit()
    response = client.get("/applications")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_patch_application_status(client, db_session, job):
    app = Application(job_id=job.id, status="reviewing")
    db_session.add(app)
    db_session.commit()
    response = client.patch(f"/applications/{app.id}", json={"status": "submitted"})
    assert response.status_code == 200
    assert response.json()["status"] == "submitted"
    # applied_at should be set
    assert response.json()["applied_at"] is not None
    db_session.refresh(job)
    assert job.status == "applied"


def test_patch_application_not_found(client):
    response = client.patch("/applications/9999", json={"status": "submitted"})
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend && pytest tests/test_applications_router.py -v
```

Expected: 404 on all

- [ ] **Step 3: Implement `backend/routers/applications.py`**

```python
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Job, Application, Resume
from backend.agents.applicator import run_applicator

router = APIRouter()


def get_resume_path(db: Session) -> str | None:
    resume = db.query(Resume).first()
    return resume.filepath if resume else None


class TriggerApplicationRequest(BaseModel):
    job_id: int


class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    tailored_resume_path: Optional[str]
    tailored_resume_text: Optional[str]   # text content returned to frontend for diff display
    form_payload: Optional[str]
    status: str
    notes: Optional[str]
    applied_at: Optional[datetime]

    class Config:
        from_attributes = True


class PatchApplicationRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


@router.post("/applications", response_model=ApplicationResponse)
def trigger_application(body: TriggerApplicationRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == body.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Guard: block if already in progress
    if job.status in ("applying", "applied"):
        raise HTTPException(status_code=409, detail=f"Job is already in status: {job.status}")

    job.status = "applying"
    db.commit()

    resume_path = get_resume_path(db)
    result = run_applicator(
        job_id=job.id,
        job_url=job.url,
        job_description=job.description or "",
        resume_path=resume_path or "",
    )

    status = "manual_required" if result["status"] == "manual_required" else "pending"
    app = Application(
        job_id=job.id,
        tailored_resume_path=None,
        tailored_resume_text=result.get("tailored_resume", ""),  # stored for frontend diff display
        form_payload=json.dumps(result.get("form_payload", {})),
        status=status,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.post("/applications/{app_id}/open")
def open_in_browser(app_id: int, db: Session = Depends(get_db)):
    """Launch Playwright with the pre-filled form for supervised submission."""
    from backend.tools.playwright_tools import open_prefilled_form
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    job = db.query(Job).filter(Job.id == app.job_id).first()
    payload = json.loads(app.form_payload or "{}")
    # Run in background thread so the HTTP response returns immediately
    import threading
    threading.Thread(target=open_prefilled_form, args=(job.url, payload), daemon=True).start()
    return {"status": "browser_opened", "url": job.url}


@router.get("/applications", response_model=list[ApplicationResponse])
def list_applications(db: Session = Depends(get_db)):
    return db.query(Application).all()


@router.patch("/applications/{app_id}", response_model=ApplicationResponse)
def update_application(app_id: int, body: PatchApplicationRequest, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if body.status:
        app.status = body.status
        if body.status == "submitted":
            app.applied_at = datetime.utcnow()
            job = db.query(Job).filter(Job.id == app.job_id).first()
            if job:
                job.status = "applied"
    if body.notes is not None:
        app.notes = body.notes

    db.commit()
    db.refresh(app)
    return app
```

- [ ] **Step 4: Add router to `backend/main.py`**

Add this import and include after the existing routers:

```python
from backend.routers import applications
# ...
app.include_router(applications.router)
```

- [ ] **Step 5: Run tests — expect pass**

```bash
cd backend && pytest tests/test_applications_router.py -v
```

Expected: 4 tests PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/routers/applications.py backend/tests/test_applications_router.py backend/main.py
git commit -m "feat: add applications router with apply trigger and status tracking"
```

---

### Task 6: ReviewPanel Component + Frontend Apply Flow

**Files:**
- Create: `frontend/src/components/ReviewPanel.jsx`
- Create: `frontend/src/components/ReviewPanel.test.jsx`
- Modify: `frontend/src/api/client.js`
- Modify: `frontend/src/components/JobCard.jsx`

- [ ] **Step 1: Add API methods to `frontend/src/api/client.js`**

Append to existing file:

```javascript
export const triggerApply = (jobId) => axios.post('/applications', { job_id: jobId }).then(r => r.data)
export const getApplications = () => axios.get('/applications').then(r => r.data)
export const updateApplication = (id, data) => axios.patch(`/applications/${id}`, data).then(r => r.data)
// Calls POST /applications/{id}/open — launches Playwright browser for supervised form submission
export const openInBrowser = (appId) => axios.post(`/applications/${appId}/open`).then(r => r.data)
```

- [ ] **Step 2: Write failing ReviewPanel tests**

```jsx
// frontend/src/components/ReviewPanel.test.jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import * as api from '../api/client'
import { ReviewPanel } from './ReviewPanel'

const mockApp = {
  id: 1, job_id: 1, status: 'pending',
  form_payload: JSON.stringify({ first_name: 'John', email: 'john@example.com' }),
  tailored_resume_path: null,
}

test('renders form fields for review', () => {
  render(<ReviewPanel application={mockApp} tailoredResume="Tailored resume text" onClose={() => {}} />)
  expect(screen.getByText('first_name')).toBeInTheDocument()
  expect(screen.getByText('John')).toBeInTheDocument()
})

test('calls updateApplication with submitted on mark submitted', async () => {
  vi.spyOn(api, 'updateApplication').mockResolvedValue({ ...mockApp, status: 'submitted' })
  const onClose = vi.fn()
  render(<ReviewPanel application={mockApp} tailoredResume="resume" onClose={onClose} />)
  fireEvent.click(screen.getByRole('button', { name: /mark as submitted/i }))
  await waitFor(() => expect(api.updateApplication).toHaveBeenCalledWith(1, { status: 'submitted' }))
})
```

- [ ] **Step 3: Run tests — expect failure**

```bash
cd frontend && npm run test:run -- ReviewPanel
```

Expected: `Cannot find module`

- [ ] **Step 4: Implement `frontend/src/components/ReviewPanel.jsx`**

```jsx
import { useState } from 'react'
import { updateApplication } from '../api/client'

export function ReviewPanel({ application, tailoredResume, onClose, onStatusChange }) {
  const [submitting, setSubmitting] = useState(false)
  const fields = (() => {
    try { return Object.entries(JSON.parse(application.form_payload || '{}')) }
    catch { return [] }
  })()

  const handleMarkSubmitted = () => {
    setSubmitting(true)
    updateApplication(application.id, { status: 'submitted' })
      .then((updated) => { onStatusChange?.(updated); onClose() })
      .finally(() => setSubmitting(false))
  }

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 20, marginTop: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <h3>Application Review</h3>
        <button onClick={onClose}>✕ Close</button>
      </div>

      {tailoredResume && (
        <div>
          <h4>Tailored Resume</h4>
          <pre style={{ background: '#f9fafb', padding: 12, borderRadius: 4, fontSize: 12, overflow: 'auto', maxHeight: 200 }}>
            {tailoredResume}
          </pre>
        </div>
      )}

      <div>
        <h4>Pre-filled Form Fields</h4>
        {fields.length === 0
          ? <p style={{ color: '#6b7280' }}>No fields could be auto-filled.</p>
          : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead><tr><th style={{ textAlign: 'left' }}>Field</th><th style={{ textAlign: 'left' }}>Value</th></tr></thead>
              <tbody>
                {fields.map(([k, v]) => (
                  <tr key={k} style={{ borderBottom: '1px solid #e5e7eb' }}>
                    <td style={{ padding: '6px 8px', color: '#6b7280' }}>{k}</td>
                    <td style={{ padding: '6px 8px' }}>{String(v)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        }
      </div>

      {application.status === 'manual_required'
        ? (
          <div style={{ marginTop: 16, padding: 12, background: '#fef3c7', borderRadius: 4 }}>
            <p><strong>Manual Required:</strong> The form could not be auto-scraped.</p>
            <a href={`/jobs/${application.job_id}`} target="_blank" rel="noopener noreferrer">
              <button>Open Job URL Manually</button>
            </a>
          </div>
        )
        : (
          <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
            <button onClick={() => openInBrowser(application.id)}>
              Open in Browser (Pre-filled)
            </button>
            <button onClick={handleMarkSubmitted} disabled={submitting}>
              {submitting ? 'Saving…' : 'Mark as Submitted'}
            </button>
          </div>
        )
      }
    </div>
  )
}
```

- [ ] **Step 5: Update `frontend/src/components/JobCard.jsx` to wire Apply button**

Replace the disabled Apply button section with:

```jsx
// Add to imports at top
import { useState } from 'react'
import { triggerApply } from '../api/client'
import { ReviewPanel } from './ReviewPanel'

// Inside JobCard component, add state:
const [applying, setApplying] = useState(false)
const [application, setApplication] = useState(null)

// Replace the disabled Apply button:
<button
  disabled={applying || ['applying', 'applied'].includes(job.status)}
  onClick={() => {
    setApplying(true)
    triggerApply(job.id)
      .then(app => setApplication(app))
      .finally(() => setApplying(false))
  }}
>
  {applying ? 'Preparing…' : 'Apply'}
</button>

// After closing div of action buttons, add:
{application && (
  <ReviewPanel
    application={application}
    tailoredResume={application.tailored_resume_text}
    onClose={() => setApplication(null)}
    onStatusChange={(updated) => setApplication(updated)}
  />
)}
```

- [ ] **Step 6: Run all frontend tests — expect pass**

```bash
cd frontend && npm run test:run
```

Expected: All tests PASSED

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ frontend/src/api/client.js
git commit -m "feat: add ReviewPanel component and Apply flow in JobCard"
```

---

### Task 7: Applications Pipeline Page

**Files:**
- Create: `frontend/src/pages/Applications.jsx`
- Create: `frontend/src/pages/Applications.test.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Write failing tests**

```jsx
// frontend/src/pages/Applications.test.jsx
import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import * as api from '../api/client'
import { Applications } from './Applications'

test('renders pipeline stages', async () => {
  vi.spyOn(api, 'getApplications').mockResolvedValue([])
  vi.spyOn(api, 'getJobs').mockResolvedValue([])
  render(<Applications />)
  await waitFor(() => {
    expect(screen.getByText('Reviewing')).toBeInTheDocument()
    expect(screen.getByText('Applied')).toBeInTheDocument()
    expect(screen.getByText('Response')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd frontend && npm run test:run -- Applications
```

Expected: `Cannot find module`

- [ ] **Step 3: Implement `frontend/src/pages/Applications.jsx`**

```jsx
import { useEffect, useState } from 'react'
import { getApplications, getJobs } from '../api/client'

const PIPELINE = [
  { key: 'reviewing', label: 'Reviewing', statuses: ['pending', 'reviewing'] },
  { key: 'manual', label: 'Manual Required', statuses: ['manual_required'] },
  { key: 'applied', label: 'Applied', statuses: ['submitted'] },
  { key: 'response', label: 'Response', statuses: ['rejected', 'interviewing', 'offered'] },
]

export function Applications() {
  const [applications, setApplications] = useState([])
  const [jobs, setJobs] = useState({})

  useEffect(() => {
    getApplications().then(setApplications)
    getJobs().then(js => setJobs(Object.fromEntries(js.map(j => [j.id, j]))))
  }, [])

  return (
    <div>
      <h1>Applications Pipeline</h1>
      <div style={{ display: 'flex', gap: 16, overflowX: 'auto' }}>
        {PIPELINE.map(stage => {
          const stageApps = applications.filter(a => stage.statuses.includes(a.status))
          return (
            <div key={stage.key} style={{ minWidth: 220, flex: 1 }}>
              <h3 style={{ borderBottom: '2px solid #e5e7eb', paddingBottom: 8 }}>
                {stage.label} ({stageApps.length})
              </h3>
              {stageApps.length === 0
                ? <p style={{ color: '#9ca3af', fontSize: 13 }}>Empty</p>
                : stageApps.map(app => (
                  <div key={app.id} style={{ border: '1px solid #e5e7eb', borderRadius: 6, padding: 10, marginBottom: 8 }}>
                    <strong>{jobs[app.job_id]?.title || `Job #${app.job_id}`}</strong>
                    <p style={{ margin: '2px 0', fontSize: 12, color: '#6b7280' }}>
                      {jobs[app.job_id]?.company}
                    </p>
                    <span style={{ fontSize: 11, color: '#8b5cf6' }}>{app.status}</span>
                  </div>
                ))
              }
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Add route to `frontend/src/App.jsx`**

```jsx
// Add import
import { Applications } from './pages/Applications'

// Add nav link
<Link to="/applications">Applications</Link>

// Add route
<Route path="/applications" element={<Applications />} />
```

- [ ] **Step 5: Run all tests — expect pass**

```bash
cd frontend && npm run test:run
cd backend && pytest -v
```

Expected: All tests PASSED

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Applications.jsx frontend/src/pages/Applications.test.jsx frontend/src/App.jsx
git commit -m "feat: add Applications pipeline page"
```

---

## Final Smoke Test

- [ ] Start both servers (`uvicorn main:app --reload` + `npm run dev`)
- [ ] Navigate to Dashboard, click Apply on a job — ReviewPanel opens with form fields
- [ ] Click "Mark as Submitted" — status updates to submitted
- [ ] Navigate to `/applications` — job appears in Applied column
- [ ] Final commit

```bash
git add .
git commit -m "feat: phase 2 complete — supervised application flow"
```
