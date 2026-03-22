# Phase 3: Cold Email Outreach — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add cold email outreach — Outreach Agent finds an HR contact via SerpAPI, generates a cover letter, tailors the resume as a PDF attachment, and sends the email via the user's connected Gmail or Outlook account after user review.

**Architecture:** `Outreach Agent` uses the Anthropic tool-use loop with tools for HR contact discovery (`find_hr_contact` via SerpAPI Google Search), cover letter generation, and email sending. OAuth tokens are stored in the `oauth_tokens` DB table (not `.env`) and auto-refreshed on expiry. The send action is gated behind a separate `POST /outreach/{id}/send` endpoint — never automatic. `jobs.status` updates to `emailing` on trigger and `emailed` on send.

**Tech Stack:** Python 3.12, FastAPI, anthropic SDK, google-auth + google-api-python-client (Gmail), msal (Outlook/Microsoft Graph), fpdf2, pytest, React 18, Vitest

**Prerequisites:** Phase 1 complete. Phase 2's `tailor_resume` tool and `resume_tools.py` are in place.

**Spec:** `docs/superpowers/specs/2026-03-22-job-applier-agent-design.md` (Phase 3 section)

---

## File Map

| File | Responsibility |
|---|---|
| `backend/models.py` | Add `OAuthToken` and `Outreach` models |
| `backend/tools/email_tools.py` | `send_email_gmail(...)`, `send_email_outlook(...)`, `get_valid_token(provider, db)` — reads/refreshes tokens from DB |
| `backend/tools/hr_finder.py` | `find_hr_contact(company, job_title)` — SerpAPI Google Search, returns `HRContact` dict |
| `backend/agents/outreach.py` | `run_outreach(job_id, job_url, job_description, company, resume_path)` — agentic loop |
| `backend/routers/outreach.py` | `POST /outreach`, `GET /outreach`, `PATCH /outreach/{id}`, `POST /outreach/{id}/send` |
| `backend/routers/auth.py` | `POST /auth/email/connect`, `GET /auth/email/callback` |
| `backend/tests/test_hr_finder.py` | Unit tests for HR contact discovery |
| `backend/tests/test_email_tools.py` | Unit tests for token refresh and email send (mocked) |
| `backend/tests/test_outreach_agent.py` | Unit tests for outreach agentic loop |
| `backend/tests/test_outreach_router.py` | API tests for outreach routes |
| `backend/tests/test_auth_router.py` | API tests for OAuth connect/callback |
| `frontend/src/api/client.js` | Add: `triggerOutreach`, `getOutreach`, `patchOutreach`, `sendOutreach`, `connectEmail` |
| `frontend/src/components/OutreachPanel.jsx` | HR contact + editable cover letter + send button |
| `frontend/src/components/OutreachPanel.test.jsx` | Component tests |
| `frontend/src/pages/Outreach.jsx` | Outreach history list |
| `frontend/src/pages/Settings.jsx` | Email OAuth connect button + reconnect prompt |
| `frontend/src/App.jsx` | Add `/outreach` and `/settings` routes |

---

## Tasks

---

### Task 1: OAuthToken and Outreach Models

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/tests/test_models.py`

- [ ] **Step 1: Write failing tests**

```python
# Add to backend/tests/test_models.py
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
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend && pytest tests/test_models.py::test_create_oauth_token tests/test_models.py::test_create_outreach -v
```

Expected: `ImportError`

- [ ] **Step 3: Add models to `backend/models.py`**

Append to end of file:

```python
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
```

- [ ] **Step 4: Run all model tests — expect pass**

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: All tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/models.py backend/tests/test_models.py
git commit -m "feat: add OAuthToken and Outreach models"
```

---

### Task 2: HR Contact Finder Tool

**Files:**
- Create: `backend/tools/hr_finder.py`
- Create: `backend/tests/test_hr_finder.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_hr_finder.py
import pytest
from unittest.mock import patch


MOCK_SEARCH_RESULTS = [
    {
        "title": "Jane Smith - Recruiter at Acme Corp | LinkedIn",
        "link": "https://linkedin.com/in/jane-smith",
        "snippet": "Jane Smith is a Technical Recruiter at Acme Corp. Email: j.smith@acme.com"
    }
]


def test_find_hr_contact_returns_dict():
    with patch("backend.tools.hr_finder.search_people", return_value=MOCK_SEARCH_RESULTS):
        from backend.tools.hr_finder import find_hr_contact
        result = find_hr_contact(company="Acme Corp", job_title="Python Engineer")
    assert isinstance(result, dict)
    assert "hr_name" in result
    assert "hr_email" in result
    assert "hr_confidence" in result


def test_find_hr_contact_returns_unknown_when_no_results():
    with patch("backend.tools.hr_finder.search_people", return_value=[]):
        from backend.tools.hr_finder import find_hr_contact
        result = find_hr_contact(company="Unknown Co", job_title="Engineer")
    assert result["hr_confidence"] == "unknown"
    assert result["hr_email"] == ""


def test_find_hr_contact_handles_search_failure():
    with patch("backend.tools.hr_finder.search_people", side_effect=Exception("API error")):
        from backend.tools.hr_finder import find_hr_contact
        result = find_hr_contact(company="Acme", job_title="Engineer")
    assert result["hr_confidence"] == "unknown"
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend && pytest tests/test_hr_finder.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `backend/tools/hr_finder.py`**

```python
import logging
import anthropic
from backend.config import settings
from backend.tools.serp import search_people

logger = logging.getLogger(__name__)

EXTRACT_SYSTEM = """You are an HR contact extractor. Given search results about a company's hiring team,
extract the most relevant recruiter or hiring manager's name and email.
Return ONLY a JSON object: {"hr_name": "...", "hr_email": "...", "hr_confidence": "search_result|inferred_pattern|unknown"}

If no email is found, infer a likely pattern (e.g. firstname.lastname@company.com) and set confidence to "inferred_pattern".
If you cannot determine any contact, set all fields to empty string and confidence to "unknown"."""


def find_hr_contact(company: str, job_title: str) -> dict:
    """
    Search SerpAPI for recruiter/hiring manager at the given company.
    Returns {"hr_name": str, "hr_email": str, "hr_confidence": str}
    """
    query = f'"{company}" recruiter hiring manager "{job_title}" site:linkedin.com OR email'
    try:
        results = search_people(query=query, num_results=5)
    except Exception as e:
        logger.warning(f"HR search failed: {e}")
        return {"hr_name": "", "hr_email": "", "hr_confidence": "unknown"}

    if not results:
        return {"hr_name": "", "hr_email": "", "hr_confidence": "unknown"}

    snippets = "\n".join(
        f"Title: {r.get('title', '')}\nURL: {r.get('link', '')}\nSnippet: {r.get('snippet', '')}"
        for r in results[:3]
    )

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=settings.OUTREACH_MODEL,
        max_tokens=256,
        system=EXTRACT_SYSTEM,
        messages=[{"role": "user", "content": f"Company: {company}\nJob: {job_title}\n\nSearch results:\n{snippets}"}],
    )

    import json
    for block in response.content:
        if getattr(block, "type", None) == "text":
            try:
                return json.loads(block.text)
            except json.JSONDecodeError:
                pass

    return {"hr_name": "", "hr_email": "", "hr_confidence": "unknown"}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd backend && pytest tests/test_hr_finder.py -v
```

Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/tools/hr_finder.py backend/tests/test_hr_finder.py
git commit -m "feat: add HR contact finder tool via SerpAPI + Claude extraction"
```

---

### Task 3: OAuth Token Management + Auth Router

**Files:**
- Create: `backend/tools/email_tools.py`
- Create: `backend/routers/auth.py`
- Create: `backend/tests/test_email_tools.py`
- Create: `backend/tests/test_auth_router.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Install email dependencies**

```bash
cd backend
pip install google-auth google-auth-oauthlib google-api-python-client msal
echo "google-auth>=2.35.0" >> requirements.txt
echo "google-auth-oauthlib>=1.2.1" >> requirements.txt
echo "google-api-python-client>=2.154.0" >> requirements.txt
echo "msal>=1.31.0" >> requirements.txt
```

- [ ] **Step 2: Write failing email tool tests**

**Prerequisite:** Phase 1's `backend/tests/conftest.py` must be in place — `test_email_tools.py` uses the `db_engine` fixture defined there.

```python
# backend/tests/test_email_tools.py
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models import OAuthToken


@pytest.fixture
def db_with_token(db_engine):
    """DB session with a valid Gmail token."""
    with Session(db_engine) as session:
        token = OAuthToken(
            provider="gmail",
            access_token="valid_access",
            refresh_token="valid_refresh",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        session.add(token)
        session.commit()
        yield session


def test_get_valid_token_returns_access_token(db_with_token):
    from backend.tools.email_tools import get_valid_token
    token = get_valid_token("gmail", db_with_token)
    assert token == "valid_access"


def test_get_valid_token_refreshes_expired_token(db_engine):
    """Expired token triggers refresh and DB update."""
    with Session(db_engine) as session:
        token = OAuthToken(
            provider="gmail",
            access_token="old_access",
            refresh_token="valid_refresh",
            expires_at=datetime.utcnow() - timedelta(hours=1),  # expired
        )
        session.add(token)
        session.commit()

    with patch("backend.tools.email_tools._refresh_gmail_token",
               return_value={"access_token": "new_access", "expires_in": 3600}):
        from backend.tools.email_tools import get_valid_token
        with Session(db_engine) as session:
            token = get_valid_token("gmail", session)
            assert token == "new_access"


def test_get_valid_token_raises_when_no_token(db_engine):
    from backend.tools.email_tools import get_valid_token
    with Session(db_engine) as session:
        with pytest.raises(ValueError, match="No OAuth token"):
            get_valid_token("gmail", session)
```

**Note on Outlook coverage:** The tests above cover the Gmail token path. The Outlook refresh path (`_refresh_outlook_token`) follows the same pattern but uses `msal`. If `EMAIL_PROVIDER=outlook` is used in production, add a parallel test by patching `backend.tools.email_tools._refresh_outlook_token`. The implementation is symmetric — only the HTTP library differs.

- [ ] **Step 3: Run tests — expect failure**

```bash
cd backend && pytest tests/test_email_tools.py -v
```

Expected: `ImportError`

- [ ] **Step 4: Implement `backend/tools/email_tools.py`**

```python
import base64
import logging
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
import requests
from sqlalchemy.orm import Session
from backend.config import settings
from backend.models import OAuthToken

logger = logging.getLogger(__name__)


def _refresh_gmail_token(refresh_token: str) -> dict:
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    response.raise_for_status()
    return response.json()


def _refresh_outlook_token(refresh_token: str) -> dict:
    import msal
    app = msal.ConfidentialClientApplication(
        settings.OUTLOOK_CLIENT_ID,
        authority="https://login.microsoftonline.com/common",
        client_credential=settings.OUTLOOK_CLIENT_SECRET,
    )
    result = app.acquire_token_by_refresh_token(refresh_token, scopes=["Mail.Send"])
    if "error" in result:
        raise ValueError(f"Token refresh failed: {result['error_description']}")
    return result


def get_valid_token(provider: str, db: Session) -> str:
    """Return a valid access token, refreshing if expired. Persists updated token to DB."""
    record = db.query(OAuthToken).filter(OAuthToken.provider == provider).first()
    if not record:
        raise ValueError(f"No OAuth token found for provider '{provider}'. Connect via /auth/email/connect.")

    if datetime.utcnow() < record.expires_at:
        return record.access_token

    # Token expired — refresh
    logger.info(f"Refreshing {provider} OAuth token...")
    if provider == "gmail":
        refreshed = _refresh_gmail_token(record.refresh_token)
    else:
        refreshed = _refresh_outlook_token(record.refresh_token)

    record.access_token = refreshed["access_token"]
    record.expires_at = datetime.utcnow() + timedelta(seconds=refreshed.get("expires_in", 3600))
    db.commit()
    return record.access_token


def send_email_gmail(access_token: str, to: str, subject: str, body: str, attachment_path: str = "") -> bool:
    """Send an email via Gmail API."""
    msg = MIMEMultipart()
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if attachment_path and Path(attachment_path).exists():
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={Path(attachment_path).name}")
        msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    response = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"raw": raw},
    )
    response.raise_for_status()
    return True


def send_email_outlook(access_token: str, to: str, subject: str, body: str, attachment_path: str = "") -> bool:
    """Send an email via Microsoft Graph API."""
    attachments = []
    if attachment_path and Path(attachment_path).exists():
        with open(attachment_path, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        attachments.append({
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": Path(attachment_path).name,
            "contentBytes": content,
        })

    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to}}],
            "attachments": attachments,
        }
    }
    response = requests.post(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json=payload,
    )
    response.raise_for_status()
    return True


def send_email(to: str, subject: str, body: str, attachment_path: str, db: Session) -> bool:
    """Dispatch email via configured provider. Reads and refreshes token from DB."""
    access_token = get_valid_token(settings.EMAIL_PROVIDER, db)
    if settings.EMAIL_PROVIDER == "gmail":
        return send_email_gmail(access_token, to, subject, body, attachment_path)
    return send_email_outlook(access_token, to, subject, body, attachment_path)
```

- [ ] **Step 5: Run email tool tests — expect pass**

```bash
cd backend && pytest tests/test_email_tools.py -v
```

Expected: 3 tests PASSED

- [ ] **Step 6: Write failing auth router tests**

```python
# backend/tests/test_auth_router.py
from unittest.mock import patch


def test_connect_gmail_returns_auth_url(client):
    with patch("backend.routers.auth.build_gmail_auth_url", return_value="https://accounts.google.com/o/oauth2/auth?..."):
        response = client.post("/auth/email/connect")
    assert response.status_code == 200
    assert "auth_url" in response.json()


def test_callback_stores_token(client, db_session):
    mock_token = {
        "access_token": "acc_123",
        "refresh_token": "ref_456",
        "expires_in": 3600,
    }
    with patch("backend.routers.auth.exchange_gmail_code", return_value=mock_token):
        response = client.get("/auth/email/callback?code=authcode123")
    assert response.status_code == 200
    from backend.models import OAuthToken
    token = db_session.query(OAuthToken).filter_by(provider="gmail").first()
    assert token is not None
    assert token.access_token == "acc_123"
```

- [ ] **Step 7: Implement `backend/routers/auth.py`**

```python
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from backend.config import settings
from backend.database import get_db
from backend.models import OAuthToken
import requests

router = APIRouter()

GMAIL_SCOPES = "https://www.googleapis.com/auth/gmail.send"


def build_gmail_auth_url() -> str:
    params = (
        f"client_id={settings.GMAIL_CLIENT_ID}"
        f"&redirect_uri={settings.OAUTH_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={GMAIL_SCOPES}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    return f"https://accounts.google.com/o/oauth2/auth?{params}"


def build_outlook_auth_url() -> str:
    params = (
        f"client_id={settings.OUTLOOK_CLIENT_ID}"
        f"&redirect_uri={settings.OAUTH_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=Mail.Send+offline_access"
    )
    return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{params}"


def exchange_gmail_code(code: str) -> dict:
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "redirect_uri": settings.OAUTH_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )
    response.raise_for_status()
    return response.json()


def exchange_outlook_code(code: str) -> dict:
    import msal
    app = msal.ConfidentialClientApplication(
        settings.OUTLOOK_CLIENT_ID,
        authority="https://login.microsoftonline.com/common",
        client_credential=settings.OUTLOOK_CLIENT_SECRET,
    )
    result = app.acquire_token_by_authorization_code(
        code, scopes=["Mail.Send"], redirect_uri=settings.OAUTH_REDIRECT_URI
    )
    if "error" in result:
        raise ValueError(result.get("error_description", "OAuth exchange failed"))
    return result


@router.post("/auth/email/connect")
def connect_email():
    """Return the OAuth provider authorization URL for the user to open."""
    if settings.EMAIL_PROVIDER == "gmail":
        url = build_gmail_auth_url()
    else:
        url = build_outlook_auth_url()
    return {"auth_url": url}


@router.get("/auth/email/callback")
def email_callback(code: str, db: Session = Depends(get_db)):
    """Exchange authorization code for tokens and persist to DB."""
    if settings.EMAIL_PROVIDER == "gmail":
        token_data = exchange_gmail_code(code)
    else:
        token_data = exchange_outlook_code(code)

    expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
    record = db.query(OAuthToken).filter(OAuthToken.provider == settings.EMAIL_PROVIDER).first()
    if not record:
        record = OAuthToken(provider=settings.EMAIL_PROVIDER)
        db.add(record)
    record.access_token = token_data["access_token"]
    record.refresh_token = token_data.get("refresh_token", record.refresh_token if hasattr(record, "refresh_token") else "")
    record.expires_at = expires_at
    db.commit()
    return {"status": "connected", "provider": settings.EMAIL_PROVIDER}
```

- [ ] **Step 8: Add auth router to `backend/main.py`**

```python
from backend.routers import auth
app.include_router(auth.router)
```

- [ ] **Step 9: Run auth tests — expect pass**

```bash
cd backend && pytest tests/test_auth_router.py -v
```

Expected: 2 tests PASSED

- [ ] **Step 10: Commit**

```bash
git add backend/tools/email_tools.py backend/routers/auth.py \
        backend/tests/test_email_tools.py backend/tests/test_auth_router.py \
        backend/main.py backend/requirements.txt
git commit -m "feat: add OAuth token management and email send tools"
```

---

### Task 4: Outreach Agent

**Files:**
- Create: `backend/agents/outreach.py`
- Create: `backend/tests/test_outreach_agent.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_outreach_agent.py
import pytest
from unittest.mock import patch, MagicMock

MOCK_HR = {"hr_name": "Jane Smith", "hr_email": "jane@acme.com", "hr_confidence": "search_result"}
MOCK_COVER = "Dear Jane,\n\nI am excited to apply for the Python Engineer role at Acme..."
MOCK_RESUME_PATH = "uploads/tailored_1.pdf"


def test_run_outreach_returns_draft():
    with patch("backend.agents.outreach.find_hr_contact", return_value=MOCK_HR), \
         patch("backend.agents.outreach.generate_cover_letter", return_value=MOCK_COVER), \
         patch("backend.agents.outreach.tailor_resume", return_value=MOCK_RESUME_PATH):
        from backend.agents.outreach import run_outreach
        result = run_outreach(
            job_id=1,
            company="Acme",
            job_description="Python Engineer at Acme",
            resume_path="uploads/master.pdf",
            output_dir="uploads",
        )
    assert result["hr_email"] == "jane@acme.com"
    assert result["cover_letter"] == MOCK_COVER
    assert result["resume_version_path"] == MOCK_RESUME_PATH
    assert result["hr_confidence"] == "search_result"


def test_run_outreach_proceeds_with_unknown_contact():
    """Outreach still generates cover letter even if HR contact is unknown."""
    unknown_hr = {"hr_name": "", "hr_email": "", "hr_confidence": "unknown"}
    with patch("backend.agents.outreach.find_hr_contact", return_value=unknown_hr), \
         patch("backend.agents.outreach.generate_cover_letter", return_value="Cover letter"), \
         patch("backend.agents.outreach.tailor_resume", return_value="uploads/t.pdf"):
        from backend.agents.outreach import run_outreach
        result = run_outreach(1, "Acme", "JD", "uploads/master.pdf", "uploads")
    assert result["hr_confidence"] == "unknown"
    assert result["cover_letter"] == "Cover letter"
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend && pytest tests/test_outreach_agent.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `backend/agents/outreach.py`**

```python
import anthropic
from backend.config import settings
from backend.tools.hr_finder import find_hr_contact
from backend.tools.resume_tools import tailor_resume

COVER_LETTER_SYSTEM = """You are a professional cover letter writer. Write a concise, personalized cover letter for a job application.
Use the applicant's resume and the job description. Address the hiring manager by name if provided.
Tone: professional, enthusiastic, specific. Length: 3-4 short paragraphs. Return ONLY the cover letter text."""


def generate_cover_letter(job_description: str, resume_path: str, company: str, hr_name: str = "") -> str:
    from backend.tools.resume_tools import _read_resume
    resume_content = _read_resume(resume_path)
    greeting = f"Dear {hr_name}," if hr_name else "Dear Hiring Manager,"
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=settings.OUTREACH_MODEL,
        max_tokens=1024,
        system=COVER_LETTER_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Company: {company}\n\nJob Description:\n{job_description}\n\nResume:\n{resume_content}\n\nSalutation: {greeting}\n\nWrite the cover letter.",
            }
        ],
    )
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


def run_outreach(
    job_id: int,
    company: str,
    job_description: str,
    resume_path: str,
    output_dir: str,
) -> dict:
    """
    Run the Outreach agent.
    Returns a dict with hr_name, hr_email, hr_confidence, cover_letter, resume_version_path.
    """
    import os
    hr = find_hr_contact(company=company, job_title=job_description[:80])
    cover_letter = generate_cover_letter(
        job_description=job_description,
        resume_path=resume_path,
        company=company,
        hr_name=hr.get("hr_name", ""),
    )
    tailored_path = os.path.join(output_dir, f"tailored_outreach_{job_id}.pdf")
    tailor_resume(
        job_description=job_description,
        master_resume_path=resume_path,
        output_format="pdf",
        output_path=tailored_path,
    )
    return {
        "hr_name": hr.get("hr_name", ""),
        "hr_email": hr.get("hr_email", ""),
        "hr_confidence": hr.get("hr_confidence", "unknown"),
        "cover_letter": cover_letter,
        "resume_version_path": tailored_path,
    }
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd backend && pytest tests/test_outreach_agent.py -v
```

Expected: 2 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/agents/outreach.py backend/tests/test_outreach_agent.py
git commit -m "feat: add Outreach agent with cover letter and HR contact discovery"
```

---

### Task 5: Outreach Router

**Files:**
- Create: `backend/routers/outreach.py`
- Create: `backend/tests/test_outreach_router.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_outreach_router.py
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
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend && pytest tests/test_outreach_router.py -v
```

Expected: 404 on all

- [ ] **Step 3: Implement `backend/routers/outreach.py`**

```python
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Job, Outreach, Resume
from backend.agents.outreach import run_outreach
from backend.tools.email_tools import send_email
from backend.config import settings

router = APIRouter()


def get_resume_path(db: Session) -> str | None:
    resume = db.query(Resume).first()
    return resume.filepath if resume else None


class TriggerOutreachRequest(BaseModel):
    job_id: int


class OutreachResponse(BaseModel):
    id: int
    job_id: int
    hr_name: Optional[str]
    hr_email: Optional[str]
    hr_confidence: Optional[str]
    cover_letter: Optional[str]
    resume_version_path: Optional[str]
    status: str
    sent_at: Optional[datetime]

    class Config:
        from_attributes = True


class PatchOutreachRequest(BaseModel):
    hr_name: Optional[str] = None
    hr_email: Optional[str] = None
    cover_letter: Optional[str] = None
    # Note: status is intentionally excluded — only /send can set status=sent


@router.post("/outreach", response_model=OutreachResponse)
def trigger_outreach(body: TriggerOutreachRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == body.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in ("emailing", "emailed"):
        raise HTTPException(status_code=409, detail=f"Job is already in status: {job.status}")

    job.status = "emailing"
    db.commit()

    resume_path = get_resume_path(db)
    result = run_outreach(
        job_id=job.id,
        company=job.company,
        job_description=job.description or "",
        resume_path=resume_path or "",
        output_dir=settings.UPLOAD_DIR,
    )

    record = Outreach(
        job_id=job.id,
        hr_name=result["hr_name"],
        hr_email=result["hr_email"],
        hr_confidence=result["hr_confidence"],
        cover_letter=result["cover_letter"],
        resume_version_path=result["resume_version_path"],
        status="draft",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/outreach", response_model=list[OutreachResponse])
def list_outreach(db: Session = Depends(get_db)):
    return db.query(Outreach).all()


@router.patch("/outreach/{outreach_id}", response_model=OutreachResponse)
def update_outreach(outreach_id: int, body: PatchOutreachRequest, db: Session = Depends(get_db)):
    record = db.query(Outreach).filter(Outreach.id == outreach_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Outreach record not found")
    if body.hr_name is not None:
        record.hr_name = body.hr_name
    if body.hr_email is not None:
        record.hr_email = body.hr_email
    if body.cover_letter is not None:
        record.cover_letter = body.cover_letter
    db.commit()
    db.refresh(record)
    return record


@router.post("/outreach/{outreach_id}/send", response_model=OutreachResponse)
def send_outreach(outreach_id: int, db: Session = Depends(get_db)):
    record = db.query(Outreach).filter(Outreach.id == outreach_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Outreach record not found")
    if not record.hr_email:
        raise HTTPException(status_code=400, detail="HR email address is required before sending")
    if record.status == "sent":
        raise HTTPException(status_code=409, detail="Already sent")

    subject = f"Application for {db.query(Job).filter(Job.id == record.job_id).first().title}"
    send_email(
        to=record.hr_email,
        subject=subject,
        body=record.cover_letter or "",
        attachment_path=record.resume_version_path or "",
        db=db,
    )

    record.status = "sent"
    record.sent_at = datetime.utcnow()
    job = db.query(Job).filter(Job.id == record.job_id).first()
    if job:
        job.status = "emailed"
    db.commit()
    db.refresh(record)
    return record
```

- [ ] **Step 4: Add router to `backend/main.py`**

```python
from backend.routers import outreach
app.include_router(outreach.router)
```

- [ ] **Step 5: Run tests — expect pass**

```bash
cd backend && pytest tests/test_outreach_router.py -v
```

Expected: 5 tests PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/routers/outreach.py backend/tests/test_outreach_router.py backend/main.py
git commit -m "feat: add outreach router with draft, edit, and send flow"
```

---

### Task 6: Frontend — Outreach Panel and Pages

**Files:**
- Create: `frontend/src/components/OutreachPanel.jsx`
- Create: `frontend/src/components/OutreachPanel.test.jsx`
- Create: `frontend/src/pages/Outreach.jsx`
- Create: `frontend/src/pages/Settings.jsx`
- Modify: `frontend/src/api/client.js`
- Modify: `frontend/src/components/JobCard.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add API methods to `frontend/src/api/client.js`**

```javascript
export const triggerOutreach = (jobId) => axios.post('/outreach', { job_id: jobId }).then(r => r.data)
export const getOutreach = () => axios.get('/outreach').then(r => r.data)
export const patchOutreach = (id, data) => axios.patch(`/outreach/${id}`, data).then(r => r.data)
export const sendOutreach = (id) => axios.post(`/outreach/${id}/send`).then(r => r.data)
export const connectEmail = () => axios.post('/auth/email/connect').then(r => r.data)
```

- [ ] **Step 2: Write failing tests**

```jsx
// frontend/src/components/OutreachPanel.test.jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import * as api from '../api/client'
import { OutreachPanel } from './OutreachPanel'

const mockRecord = {
  id: 1, job_id: 1, hr_name: 'Jane Smith', hr_email: 'jane@acme.com',
  hr_confidence: 'search_result', cover_letter: 'Dear Jane...', status: 'draft', sent_at: null,
}

test('renders HR contact and cover letter', () => {
  render(<OutreachPanel record={mockRecord} onClose={() => {}} />)
  expect(screen.getByText('jane@acme.com')).toBeInTheDocument()
  expect(screen.getByDisplayValue('Dear Jane...')).toBeInTheDocument()
})

test('calls sendOutreach on Send click', async () => {
  vi.spyOn(api, 'sendOutreach').mockResolvedValue({ ...mockRecord, status: 'sent' })
  render(<OutreachPanel record={mockRecord} onClose={() => {}} />)
  fireEvent.click(screen.getByRole('button', { name: /send email/i }))
  await waitFor(() => expect(api.sendOutreach).toHaveBeenCalledWith(1))
})
```

- [ ] **Step 3: Run tests — expect failure**

```bash
cd frontend && npm run test:run -- OutreachPanel
```

Expected: `Cannot find module`

- [ ] **Step 4: Implement `frontend/src/components/OutreachPanel.jsx`**

```jsx
import { useState } from 'react'
import { patchOutreach, sendOutreach } from '../api/client'

const CONFIDENCE_COLORS = {
  search_result: '#22c55e',
  inferred_pattern: '#f59e0b',
  unknown: '#ef4444',
}

export function OutreachPanel({ record: initialRecord, onClose, onSent }) {
  const [record, setRecord] = useState(initialRecord)
  const [sending, setSending] = useState(false)

  const handleFieldChange = (field) => (e) => {
    const value = e.target.value
    setRecord(r => ({ ...r, [field]: value }))
    patchOutreach(record.id, { [field]: value })
  }

  const handleSend = () => {
    setSending(true)
    sendOutreach(record.id)
      .then(updated => { setRecord(updated); onSent?.(updated); onClose() })
      .catch(err => alert(err.response?.data?.detail || 'Send failed'))
      .finally(() => setSending(false))
  }

  const confidenceColor = CONFIDENCE_COLORS[record.hr_confidence] || '#6b7280'

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 20, marginTop: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <h3>Email HR</h3>
        <button onClick={onClose}>✕ Close</button>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label><strong>HR Contact</strong></label>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 4 }}>
          <input value={record.hr_name || ''} onChange={handleFieldChange('hr_name')}
            placeholder="Name" style={{ flex: 1 }} />
          <input value={record.hr_email || ''} onChange={handleFieldChange('hr_email')}
            placeholder="Email" style={{ flex: 2 }} />
          <span style={{ fontSize: 11, color: confidenceColor, whiteSpace: 'nowrap' }}>
            {record.hr_confidence}
          </span>
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label><strong>Cover Letter</strong></label>
        <textarea
          value={record.cover_letter || ''}
          onChange={handleFieldChange('cover_letter')}
          rows={10}
          style={{ width: '100%', marginTop: 4, fontFamily: 'inherit', fontSize: 13 }}
        />
      </div>

      {record.resume_version_path && (
        <p style={{ fontSize: 13, color: '#6b7280' }}>
          Attachment: {record.resume_version_path.split('/').pop()}
        </p>
      )}

      {record.status === 'sent'
        ? <p style={{ color: '#22c55e' }}>✓ Email sent at {new Date(record.sent_at).toLocaleString()}</p>
        : (
          <button onClick={handleSend} disabled={sending || !record.hr_email} aria-label="Send Email">
            {sending ? 'Sending…' : 'Send Email'}
          </button>
        )
      }
    </div>
  )
}
```

- [ ] **Step 5: Implement `frontend/src/pages/Outreach.jsx`**

```jsx
import { useEffect, useState } from 'react'
import { getOutreach, getJobs } from '../api/client'

export function Outreach() {
  const [records, setRecords] = useState([])
  const [jobs, setJobs] = useState({})

  useEffect(() => {
    getOutreach().then(setRecords)
    getJobs().then(js => setJobs(Object.fromEntries(js.map(j => [j.id, j]))))
  }, [])

  return (
    <div>
      <h1>Outreach History</h1>
      {records.length === 0
        ? <p style={{ color: '#9ca3af' }}>No outreach records yet.</p>
        : records.map(r => (
          <div key={r.id} style={{ border: '1px solid #e5e7eb', borderRadius: 6, padding: 12, marginBottom: 8 }}>
            <strong>{jobs[r.job_id]?.title}</strong> at {jobs[r.job_id]?.company}
            <p style={{ margin: '4px 0', fontSize: 13, color: '#6b7280' }}>
              To: {r.hr_name || 'Unknown'} &lt;{r.hr_email || '—'}&gt;
            </p>
            <span style={{
              fontSize: 11, padding: '2px 6px', borderRadius: 4,
              background: r.status === 'sent' ? '#22c55e' : '#f59e0b', color: '#fff'
            }}>
              {r.status}
            </span>
            {r.sent_at && <span style={{ fontSize: 11, color: '#6b7280', marginLeft: 8 }}>
              {new Date(r.sent_at).toLocaleString()}
            </span>}
          </div>
        ))
      }
    </div>
  )
}
```

- [ ] **Step 6: Implement `frontend/src/pages/Settings.jsx`**

```jsx
import { useState } from 'react'
import { connectEmail } from '../api/client'

export function Settings() {
  const [connecting, setConnecting] = useState(false)
  const webhookUrl = `${window.location.origin.replace('5173', '8000')}/webhook/job-alerts`
  const webhookSecret = '(set WEBHOOK_SECRET in backend .env)'

  const handleConnect = () => {
    setConnecting(true)
    connectEmail()
      .then(({ auth_url }) => window.open(auth_url, '_blank'))
      .finally(() => setConnecting(false))
  }

  return (
    <div>
      <h1>Settings</h1>
      <h2>Email Connection</h2>
      <p>Connect your Gmail or Outlook account to send cold emails.</p>
      <button onClick={handleConnect} disabled={connecting}>
        {connecting ? 'Opening…' : 'Connect Email Account'}
      </button>

      <h2>Webhook</h2>
      <p>Use this URL to receive job alerts from external agents:</p>
      <code style={{ display: 'block', background: '#f9fafb', padding: 8, borderRadius: 4, marginTop: 4 }}>
        {webhookUrl}
      </code>
      <p style={{ marginTop: 8 }}>Include header: <code>X-Webhook-Secret: {webhookSecret}</code></p>
    </div>
  )
}
```

- [ ] **Step 7: Update `frontend/src/App.jsx`**

```jsx
import { Outreach } from './pages/Outreach'
import { Settings } from './pages/Settings'

// Add nav links:
<Link to="/outreach">Outreach</Link>
<Link to="/settings">Settings</Link>

// Add routes:
<Route path="/outreach" element={<Outreach />} />
<Route path="/settings" element={<Settings />} />
```

- [ ] **Step 8: Wire Email HR button in `frontend/src/components/JobCard.jsx`**

```jsx
// Add import
import { triggerOutreach } from '../api/client'
import { OutreachPanel } from './OutreachPanel'

// Add state
const [outreaching, setOutreaching] = useState(false)
const [outreachRecord, setOutreachRecord] = useState(null)

// Replace disabled Email HR button
<button
  disabled={outreaching || ['emailing', 'emailed'].includes(job.status)}
  onClick={() => {
    setOutreaching(true)
    triggerOutreach(job.id)
      .then(r => setOutreachRecord(r))
      .finally(() => setOutreaching(false))
  }}
>
  {outreaching ? 'Preparing…' : 'Email HR'}
</button>

// After action buttons div
{outreachRecord && (
  <OutreachPanel
    record={outreachRecord}
    onClose={() => setOutreachRecord(null)}
    onSent={(updated) => setOutreachRecord(updated)}
  />
)}
```

- [ ] **Step 9: Run all tests**

```bash
cd frontend && npm run test:run
cd backend && pytest -v
```

Expected: All tests PASSED

- [ ] **Step 10: Commit**

```bash
git add frontend/src/ backend/
git commit -m "feat: add OutreachPanel, Outreach history page, and Settings page"
```

---

## Final Smoke Test

- [ ] Start both servers
- [ ] Navigate to Settings — connect email account (OAuth flow)
- [ ] Click "Email HR" on a job — OutreachPanel opens with HR contact (or unknown) and cover letter
- [ ] Edit the cover letter text — auto-saves via PATCH
- [ ] Click "Send Email" — email dispatched from your real account
- [ ] Navigate to `/outreach` — record shows "sent" status

```bash
git add .
git commit -m "feat: phase 3 complete — cold email outreach"
```
