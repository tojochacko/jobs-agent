# Phase 4: Webhook + External Agent Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose a webhook endpoint that accepts job alerts from external agents (e.g. email-processing AI), scores them against user preferences using the Orchestrator, deduplicates by URL, and surfaces matching jobs in the dashboard with a "via webhook" badge.

**Architecture:** A single `POST /webhook/job-alerts` endpoint validates the `X-Webhook-Secret` header, runs each incoming job through the same Orchestrator scoring logic as Phase 1's JobScout, and persists matches above `JOB_MATCH_THRESHOLD` (unless `WEBHOOK_BYPASS_THRESHOLD=true`). The Orchestrator is a thin Claude Haiku agent that scores one job at a time. Duplicate URLs are silently skipped.

**Tech Stack:** Python 3.12, FastAPI, anthropic SDK, SQLAlchemy, pytest, React 18, Vitest

**Prerequisites:** Phase 1 complete. `jobs` table, `preferences` router, and `scheduler.py` with `get_preferences_dict()` are in place.

**Spec:** `docs/superpowers/specs/2026-03-22-job-applier-agent-design.md` (Phase 4 section)

---

## File Map

| File | Responsibility |
|---|---|
| `backend/agents/orchestrator.py` | `score_job(job_data, preferences)` — Haiku scores one job against criteria, returns float 0.0–1.0 |
| `backend/routers/webhook.py` | `POST /webhook/job-alerts` — validates secret, scores, deduplicates, persists. **Note:** The spec's project structure diagram shows `backend/webhook.py` at the top level; this plan intentionally uses `backend/routers/webhook.py` for consistency with other routers. |
| `backend/tests/test_orchestrator.py` | Unit tests for job scoring |
| `backend/tests/test_webhook_router.py` | API tests for webhook endpoint |
| `backend/main.py` | Add webhook router |
| `frontend/src/pages/Settings.jsx` | Already shows webhook URL — no changes needed if Phase 3 is complete |

---

## Tasks

---

### Task 1: Orchestrator Scoring Agent

**Files:**
- Create: `backend/agents/orchestrator.py`
- Create: `backend/tests/test_orchestrator.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_orchestrator.py
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

HIGH_MATCH_JOB = {
    "title": "Senior Python Engineer",
    "company": "Startup Co",
    "location": "Remote",
    "description": "FastAPI, PostgreSQL, Docker, fully remote senior backend role",
    "url": "https://startup.com/jobs/1",
}

LOW_MATCH_JOB = {
    "title": "Junior Marketing Analyst",
    "company": "Big Corp",
    "location": "New York",
    "description": "Excel, PowerPoint, marketing campaigns",
    "url": "https://bigcorp.com/jobs/2",
}


def _mock_score_response(score: float):
    block = MagicMock(type="text", text=str(score))
    resp = MagicMock(stop_reason="end_turn", content=[block])
    return resp


def test_score_job_returns_float():
    with patch("backend.agents.orchestrator.anthropic.Anthropic") as MockClient:
        client = MagicMock()
        MockClient.return_value = client
        client.messages.create.return_value = _mock_score_response(0.92)
        from backend.agents.orchestrator import score_job
        score = score_job(HIGH_MATCH_JOB, PREFERENCES)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
    assert score == 0.92


def test_score_job_handles_malformed_response():
    """If agent returns non-numeric text, return 0.0 safely."""
    block = MagicMock(type="text", text="I cannot score this job.")
    resp = MagicMock(stop_reason="end_turn", content=[block])
    with patch("backend.agents.orchestrator.anthropic.Anthropic") as MockClient:
        client = MagicMock()
        MockClient.return_value = client
        client.messages.create.return_value = resp
        from backend.agents.orchestrator import score_job
        score = score_job(LOW_MATCH_JOB, PREFERENCES)
    assert score == 0.0


def test_score_job_clamps_to_valid_range():
    """Scores outside 0.0–1.0 are clamped."""
    with patch("backend.agents.orchestrator.anthropic.Anthropic") as MockClient:
        client = MagicMock()
        MockClient.return_value = client
        client.messages.create.return_value = _mock_score_response(1.5)
        from backend.agents.orchestrator import score_job
        score = score_job(HIGH_MATCH_JOB, PREFERENCES)
    assert score == 1.0
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend && pytest tests/test_orchestrator.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `backend/agents/orchestrator.py`**

```python
import json
import anthropic
from backend.config import settings

SCORE_SYSTEM = """You are a job relevance scorer. Given a job posting and user preferences, return ONLY a single decimal number between 0.0 and 1.0 representing how well the job matches the preferences.

Scoring weights:
- Job title match: 35%
- Remote/location match: 30%
- Experience level match: 20%
- Domain/tech stack match: 10%
- Company size match: 5%

Return ONLY the number. Example: 0.87"""


def score_job(job_data: dict, preferences: dict) -> float:
    """
    Score a single job against user preferences.
    Returns a float 0.0–1.0. Returns 0.0 on any error.
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    prompt = (
        f"User Preferences:\n{json.dumps(preferences, indent=2)}\n\n"
        f"Job Posting:\nTitle: {job_data.get('title', '')}\n"
        f"Company: {job_data.get('company', '')}\n"
        f"Location: {job_data.get('location', '')}\n"
        f"Description: {job_data.get('description', '')[:500]}\n\n"
        f"Score this job (0.0–1.0):"
    )
    try:
        response = client.messages.create(
            model=settings.ORCHESTRATOR_MODEL,
            max_tokens=16,
            system=SCORE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        for block in response.content:
            if getattr(block, "type", None) == "text":
                raw = block.text.strip()
                score = float(raw)
                return max(0.0, min(1.0, score))  # clamp to [0, 1]
    except (ValueError, TypeError, Exception):
        pass
    return 0.0
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd backend && pytest tests/test_orchestrator.py -v
```

Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/agents/orchestrator.py backend/tests/test_orchestrator.py
git commit -m "feat: add Orchestrator scoring agent for webhook job evaluation"
```

---

### Task 2: Webhook Router

**Files:**
- Create: `backend/routers/webhook.py`
- Create: `backend/tests/test_webhook_router.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_webhook_router.py
import pytest
from unittest.mock import patch
from backend.models import Job


VALID_PAYLOAD = {
    "source": "gmail-agent",
    "jobs": [
        {
            "title": "Python Engineer",
            "company": "Acme Corp",
            "url": "https://acme.com/jobs/webhook-1",
            "description": "Build APIs",
            "location": "Remote",
        }
    ],
}


@pytest.fixture
def webhook_headers(monkeypatch):
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_SECRET", "test-secret")
    return {"X-Webhook-Secret": "test-secret"}


def test_webhook_requires_secret(client):
    response = client.post("/webhook/job-alerts", json=VALID_PAYLOAD)
    assert response.status_code == 401


def test_webhook_rejects_wrong_secret(client, monkeypatch):
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_SECRET", "correct-secret")
    response = client.post(
        "/webhook/job-alerts",
        json=VALID_PAYLOAD,
        headers={"X-Webhook-Secret": "wrong-secret"},
    )
    assert response.status_code == 401


def test_webhook_persists_matching_jobs(client, db_session, webhook_headers, monkeypatch):
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_SECRET", "test-secret")
    with patch("backend.routers.webhook.score_job", return_value=0.85), \
         patch("backend.routers.webhook.get_preferences_dict",
               return_value={"job_titles": ["Python Engineer"]}):
        response = client.post("/webhook/job-alerts", json=VALID_PAYLOAD, headers=webhook_headers)
    assert response.status_code == 200
    assert response.json()["inserted"] == 1
    jobs = db_session.query(Job).all()
    assert len(jobs) == 1
    assert jobs[0].source == "webhook"
    assert jobs[0].match_score == 0.85


def test_webhook_skips_low_score(client, db_session, webhook_headers, monkeypatch):
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("backend.routers.webhook.settings.JOB_MATCH_THRESHOLD", 0.6)
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_BYPASS_THRESHOLD", False)
    with patch("backend.routers.webhook.score_job", return_value=0.3), \
         patch("backend.routers.webhook.get_preferences_dict",
               return_value={"job_titles": ["Python Engineer"]}):
        response = client.post("/webhook/job-alerts", json=VALID_PAYLOAD, headers=webhook_headers)
    assert response.status_code == 200
    assert response.json()["inserted"] == 0


def test_webhook_bypass_threshold_stores_all(client, db_session, webhook_headers, monkeypatch):
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_BYPASS_THRESHOLD", True)
    with patch("backend.routers.webhook.score_job", return_value=0.2), \
         patch("backend.routers.webhook.get_preferences_dict",
               return_value={"job_titles": ["Python Engineer"]}):
        response = client.post("/webhook/job-alerts", json=VALID_PAYLOAD, headers=webhook_headers)
    assert response.status_code == 200
    assert response.json()["inserted"] == 1


def test_webhook_deduplicates_by_url(client, db_session, webhook_headers, monkeypatch):
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_SECRET", "test-secret")
    existing = Job(
        title="Python Engineer", company="Acme", url="https://acme.com/jobs/webhook-1",
        source="webhook",
    )
    db_session.add(existing)
    db_session.commit()
    with patch("backend.routers.webhook.score_job", return_value=0.9), \
         patch("backend.routers.webhook.get_preferences_dict",
               return_value={"job_titles": ["Python Engineer"]}):
        response = client.post("/webhook/job-alerts", json=VALID_PAYLOAD, headers=webhook_headers)
    assert response.status_code == 200
    assert response.json()["inserted"] == 0
    assert db_session.query(Job).count() == 1  # no duplicate


def test_webhook_proceeds_without_preferences(client, db_session, webhook_headers, monkeypatch):
    """If no preferences configured and bypass=True, all incoming jobs are stored with score=0.0."""
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("backend.routers.webhook.settings.WEBHOOK_BYPASS_THRESHOLD", True)
    with patch("backend.routers.webhook.get_preferences_dict", return_value=None), \
         patch("backend.routers.webhook.score_job", return_value=0.0):
        response = client.post("/webhook/job-alerts", json=VALID_PAYLOAD, headers=webhook_headers)
    assert response.status_code == 200
    assert response.json()["inserted"] == 1   # job is stored despite no preferences
    assert db_session.query(Job).count() == 1
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd backend && pytest tests/test_webhook_router.py -v
```

Expected: `ImportError` or 404

- [ ] **Step 3: Implement `backend/routers/webhook.py`**

```python
import logging
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import Optional
from backend.config import settings
from backend.database import get_db
from backend.models import Job
from backend.agents.orchestrator import score_job
from backend.scheduler import get_preferences_dict

logger = logging.getLogger(__name__)
router = APIRouter()


class WebhookJob(BaseModel):
    title: str
    company: str
    url: str
    description: str = ""
    location: str = ""


class WebhookPayload(BaseModel):
    source: str
    jobs: list[WebhookJob]


@router.post("/webhook/job-alerts")
def receive_job_alerts(
    payload: WebhookPayload,
    x_webhook_secret: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    # Validate secret
    if not x_webhook_secret or x_webhook_secret != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Webhook-Secret header")

    preferences = get_preferences_dict()
    inserted = 0
    skipped_score = 0
    skipped_duplicate = 0

    for job_data in payload.jobs:
        job_dict = job_data.model_dump()

        # Score against preferences (skip scoring if no preferences and bypass is off)
        if preferences and not settings.WEBHOOK_BYPASS_THRESHOLD:
            match_score = score_job(job_dict, preferences)
            if match_score < settings.JOB_MATCH_THRESHOLD:
                skipped_score += 1
                continue
        elif not preferences and not settings.WEBHOOK_BYPASS_THRESHOLD:
            skipped_score += 1
            continue
        else:
            # bypass_threshold=True or no preferences with bypass — store with score 0 if no prefs
            match_score = score_job(job_dict, preferences) if preferences else 0.0

        job = Job(
            title=job_dict["title"],
            company=job_dict["company"],
            url=job_dict["url"],
            description=job_dict.get("description", ""),
            location=job_dict.get("location", ""),
            match_score=match_score,
            source="webhook",
            status="new",
        )
        db.add(job)
        try:
            db.commit()
            inserted += 1
        except IntegrityError:
            db.rollback()
            skipped_duplicate += 1

    logger.info(
        f"Webhook from '{payload.source}': {inserted} inserted, "
        f"{skipped_score} below threshold, {skipped_duplicate} duplicates"
    )
    return {
        "status": "ok",
        "inserted": inserted,
        "skipped_score": skipped_score,
        "skipped_duplicate": skipped_duplicate,
    }
```

- [ ] **Step 4: Add router to `backend/main.py`**

```python
from backend.routers import webhook
app.include_router(webhook.router)
```

- [ ] **Step 5: Run tests — expect pass**

```bash
cd backend && pytest tests/test_webhook_router.py -v
```

Expected: 6 tests PASSED

- [ ] **Step 6: Run full backend test suite**

```bash
cd backend && pytest -v
```

Expected: All tests PASSED

- [ ] **Step 7: Commit**

```bash
git add backend/routers/webhook.py backend/tests/test_webhook_router.py backend/main.py
git commit -m "feat: add webhook endpoint for external job alert ingestion"
```

---

### Task 3: Settings Page (if not already done in Phase 3)

**Note:** If Phase 3 is complete, `frontend/src/pages/Settings.jsx` already shows the webhook URL and secret. Verify it does.

- [ ] **Step 1: Verify Settings page shows webhook URL**

```bash
cd frontend && npm run test:run -- Settings
```

If Settings page doesn't exist yet (Phase 3 skipped), implement it now:

```jsx
// frontend/src/pages/Settings.jsx
export function Settings() {
  const webhookUrl = `${window.location.origin.replace('5173', '8000')}/webhook/job-alerts`

  return (
    <div>
      <h1>Settings</h1>
      <h2>Webhook</h2>
      <p>External agents can POST job alerts to:</p>
      <code style={{ display: 'block', background: '#f9fafb', padding: 8, borderRadius: 4 }}>
        {webhookUrl}
      </code>
      <p style={{ marginTop: 8 }}>
        Required header: <code>X-Webhook-Secret: &lt;value of WEBHOOK_SECRET in .env&gt;</code>
      </p>
      <h3>Payload Schema</h3>
      <pre style={{ background: '#f9fafb', padding: 12, borderRadius: 4, fontSize: 12 }}>{`{
  "source": "my-email-agent",
  "jobs": [
    {
      "title": "string",
      "company": "string",
      "url": "string",
      "description": "string",
      "location": "string"
    }
  ]
}`}</pre>
    </div>
  )
}
```

- [ ] **Step 2: Ensure `/settings` route is in `frontend/src/App.jsx`**

```jsx
import { Settings } from './pages/Settings'
// In nav:
<Link to="/settings">Settings</Link>
// In routes:
<Route path="/settings" element={<Settings />} />
```

- [ ] **Step 3: Run all frontend tests**

```bash
cd frontend && npm run test:run
```

Expected: All tests PASSED

- [ ] **Step 4: Commit (if changes made)**

```bash
git add frontend/src/pages/Settings.jsx frontend/src/App.jsx
git commit -m "feat: add Settings page with webhook URL and schema"
```

---

## Final Smoke Test

- [ ] **Start backend**

```bash
cd backend && uvicorn main:app --reload --port 8000
```

- [ ] **Test the webhook endpoint manually**

```bash
curl -X POST http://localhost:8000/webhook/job-alerts \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: your-secret-here" \
  -d '{
    "source": "test-agent",
    "jobs": [{
      "title": "Senior Python Engineer",
      "company": "Test Corp",
      "url": "https://testcorp.com/jobs/99",
      "description": "Remote Python FastAPI role",
      "location": "Remote"
    }]
  }'
```

Expected: `{"status": "ok", "inserted": 1, "skipped_score": 0, "skipped_duplicate": 0}`

- [ ] **Verify job appears in dashboard**

Open `http://localhost:5173` — the job appears with a "via webhook" badge.

- [ ] **Test deduplication**

Run the same curl command again.

Expected: `{"status": "ok", "inserted": 0, "skipped_score": 0, "skipped_duplicate": 1}`

- [ ] **Run full test suite one final time**

```bash
cd backend && pytest -v
cd frontend && npm run test:run
```

Expected: All tests PASSED

- [ ] **Final commit**

```bash
git add .
git commit -m "feat: phase 4 complete — webhook integration and external agent ingestion"
```

---

## Post-Phase 4: All Phases Complete

The full JobApplierAgent system is now operational:

| Phase | Feature | Status |
|---|---|---|
| 1 | Job Discovery Dashboard + SerpAPI polling | ✓ |
| 2 | Supervised Application Flow (Playwright + AI tailoring) | ✓ |
| 3 | Cold Email Outreach (Gmail/Outlook OAuth + cover letter) | ✓ |
| 4 | Webhook Ingestion (external agent integration) | ✓ |

**To start the full system:**

```bash
# Terminal 1 — Backend
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open `http://localhost:5173` to use the application.
