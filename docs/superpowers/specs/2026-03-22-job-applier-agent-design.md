# JobApplierAgent — Design Spec
**Date:** 2026-03-22
**Status:** Approved

---

## Overview

JobApplierAgent is a single-user autonomous job search assistant. It discovers matching jobs, pre-fills applications for supervised submission, sends cold emails to HR contacts, and accepts job alerts from external agents via webhook. The user retains final control over every submission and send action.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Frontend | React + Vite (JavaScript) |
| Backend | Python 3.12 + FastAPI |
| Agent Framework | Claude Agent SDK (Anthropic) |
| LLM | `claude-haiku-4-5` for all agents (upgrade path via `ORCHESTRATOR_MODEL` env var to `claude-sonnet-4-6`) |
| Job Discovery | SerpAPI (Google Jobs endpoint) |
| Browser Automation | Playwright (supervised mode only) |
| Email | Gmail / Outlook OAuth (Google API / Microsoft Graph) |
| Database | SQLite via SQLAlchemy (PostgreSQL-compatible schema) |
| Scheduling | APScheduler |
| Auth | None (single user) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  React Frontend (Vite)                   │
│  Criteria Form │ Resume Upload │ Job Dashboard │ Review  │
└──────────────────────────┬──────────────────────────────┘
                           │ REST + SSE
┌──────────────────────────▼──────────────────────────────┐
│                  FastAPI Backend                          │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │        Orchestrator Agent (claude-haiku-4-5)    │    │
│  │  ┌──────────────┐ ┌────────────┐ ┌──────────┐  │    │
│  │  │  JobScout    │ │ Applicator │ │ Outreach │  │    │
│  │  │    Agent     │ │   Agent    │ │  Agent   │  │    │
│  │  └──────────────┘ └────────────┘ └──────────┘  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  APScheduler │ Webhook API │ SQLite DB │ File Storage    │
└─────────────────────────────────────────────────────────┘
         │                  │                   │
      SerpAPI          Playwright          Gmail/Outlook
                       (supervised)           OAuth
```

### Agent Responsibilities

| Agent | Model | Responsibility | Tools |
|---|---|---|---|
| Orchestrator | haiku-4-5 | Delegates tasks to sub-agents, scores webhook jobs | all sub-agent callers |
| JobScout | haiku-4-5 | Polls SerpAPI, scores job relevance against criteria | `search_jobs` |
| Applicator | haiku-4-5 | Scrapes career forms, tailors resume, pre-fills fields | `fetch_application_form`, `tailor_resume` |
| Outreach | haiku-4-5 | Finds HR contact, drafts cover letter, sends email | `find_hr_contact`, `generate_cover_letter`, `tailor_resume`, `send_email` |

---

## Data Model (SQLite)

```sql
-- User preferences
CREATE TABLE preferences (
    id INTEGER PRIMARY KEY,
    job_titles JSON NOT NULL,
    location TEXT,
    remote_hybrid TEXT,           -- 'remote' | 'hybrid' | 'onsite' | 'any'
    experience_level TEXT,
    domain TEXT,
    company_size JSON,
    poll_interval_hrs INTEGER DEFAULT 6,
    updated_at TIMESTAMP
);

-- Master resume
CREATE TABLE resume (
    id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    content TEXT NOT NULL,        -- file path or base64
    uploaded_at TIMESTAMP
);

-- Discovered jobs
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    description TEXT,
    location TEXT,
    match_score REAL,
    source TEXT NOT NULL,         -- 'serpapi' | 'webhook'
    status TEXT DEFAULT 'new',    -- 'new' | 'saved' | 'dismissed' | 'error'
    error_reason TEXT,
    created_at TIMESTAMP
);

-- Application tracking
CREATE TABLE applications (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    tailored_resume TEXT,
    form_payload JSON,
    status TEXT DEFAULT 'pending', -- 'pending' | 'reviewed' | 'submitted' | 'rejected'
    notes TEXT,
    applied_at TIMESTAMP
);

-- Outreach tracking
CREATE TABLE outreach (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    hr_name TEXT,
    hr_email TEXT,
    hr_confidence TEXT,           -- 'linkedin' | 'inferred' | 'unknown'
    cover_letter TEXT,
    resume_version TEXT,
    status TEXT DEFAULT 'draft',  -- 'draft' | 'sent'
    sent_at TIMESTAMP
);
```

---

## Project Structure

```
JobApplierAgent/
├── frontend/                        # React + Vite
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.jsx        # Job discovery dashboard
│       │   ├── Preferences.jsx      # Job criteria + resume upload
│       │   ├── Applications.jsx     # Application pipeline tracker
│       │   └── Outreach.jsx         # Cold email history
│       ├── components/
│       │   ├── JobCard.jsx
│       │   ├── ReviewPanel.jsx      # Resume diff + form preview
│       │   └── StatusBadge.jsx
│       └── api/                     # Typed fetch wrappers
│
├── backend/
│   ├── main.py                      # FastAPI app entrypoint + routes
│   ├── agents/
│   │   ├── orchestrator.py          # Orchestrator Agent
│   │   ├── job_scout.py             # JobScout Agent
│   │   ├── applicator.py            # Applicator Agent
│   │   └── outreach.py              # Outreach Agent
│   ├── tools/
│   │   ├── serp.py                  # SerpAPI wrapper
│   │   ├── playwright_tools.py      # Form scraping + supervised prefill
│   │   ├── email_tools.py           # Gmail/Outlook OAuth + send
│   │   └── resume_tools.py          # Resume tailoring (shared across agents)
│   ├── scheduler.py                 # APScheduler setup
│   ├── models.py                    # SQLAlchemy models
│   ├── webhook.py                   # POST /webhook/job-alerts
│   └── config.py                    # Env vars, model config
│
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-03-22-job-applier-agent-design.md
│
└── .env.example
```

---

## Implementation Phases

### Phase 1 — Foundation + Job Discovery Dashboard

**Scope:** Core infrastructure, job criteria input, resume upload, SerpAPI-powered job polling, discovery dashboard.

**Backend deliverables:**
- FastAPI app with routes: `GET/POST /preferences`, `POST /resume`, `GET /jobs`, `DELETE /jobs/{id}`
- `JobScout Agent` with `search_jobs(query, location, filters)` tool backed by SerpAPI
- APScheduler running JobScout on configurable interval (default: 6 hours)
- SQLite schema: `preferences`, `resume`, `jobs` tables
- Match scoring: Haiku scores each SerpAPI result against user preferences (0.0–1.0), filters below threshold

**Frontend deliverables:**
- Preferences form (job titles, location, remote/hybrid, experience level, domain, company size, poll interval)
- Resume upload (PDF/DOCX accepted)
- Job dashboard: card/table view with match score, JD preview, source badge, action buttons (Apply / Email HR — disabled until Phase 2/3)
- Manual "Refresh Now" trigger for job polling

**Success criteria:** User configures criteria, uploads resume, sees a populated dashboard of relevant jobs within one poll cycle.

---

### Phase 2 — Supervised Application Flow

**Scope:** Applicator Agent, AI resume tailoring, Playwright supervised pre-fill, application tracking.

**Backend deliverables:**
- `Applicator Agent` with tools: `fetch_application_form(url)` (Playwright scrapes fields), `tailor_resume(job_description, master_resume)` (Haiku rewrites)
- `POST /applications` — triggers applicator flow for a given job
- `GET /applications`, `PATCH /applications/{id}` — status updates
- `applications` table
- Fallback: if Playwright cannot parse the form, return raw URL with `status: manual_required`

**Frontend deliverables:**
- "Apply" button triggers applicator flow with loading state
- Review panel: side-by-side tailored resume diff vs master + prefilled form fields preview
- "Open in Browser" button — Playwright opens pre-filled form for user final submit
- Application pipeline tab: Discovered → Reviewing → Applied → Response

**Key constraint:** Agent never submits a form. It always stops at pre-fill and hands off.

**Success criteria:** User clicks Apply, reviews tailored resume + pre-filled form, opens in browser, and submits manually.

---

### Phase 3 — Cold Email Outreach

**Scope:** Outreach Agent, Gmail/Outlook OAuth, HR contact discovery, AI cover letter generation, email review and send.

**Backend deliverables:**
- `Outreach Agent` with tools: `find_hr_contact(company, job_title)` (SerpAPI search for recruiter/HM), `generate_cover_letter(job_description, master_resume, company)`, `tailor_resume`, `send_email(to, subject, body, attachment)`
- Gmail OAuth via Google API (`gmail.send` scope); Outlook OAuth via Microsoft Graph (`mail.send` scope); provider chosen via `EMAIL_PROVIDER` env var
- OAuth token storage in `.env`; auto-refresh on expiry; frontend prompt on refresh failure
- `POST /outreach` — triggers outreach flow for a given job
- `GET /outreach`, `PATCH /outreach/{id}`
- `outreach` table with `hr_confidence` field

**Frontend deliverables:**
- "Email HR" button triggers outreach flow
- Review panel: HR contact (name, email, confidence level), editable cover letter body, resume attachment preview
- Send button — dispatches via connected email account
- Outreach history tab

**Key constraint:** HR contact finding is best-effort. Confidence level always shown to user. Email never sent without user clicking Send.

**Success criteria:** User clicks Email HR, reviews HR contact + cover letter, edits if needed, sends. Email arrives from user's real email address.

---

### Phase 4 — Webhook + External Agent Integration

**Scope:** Incoming webhook endpoint, external job alert ingestion, deduplication.

**Backend deliverables:**
- `POST /webhook/job-alerts` — accepts job alert payloads from external agents
- Request schema:
  ```json
  {
    "source": "string",
    "jobs": [
      {
        "title": "string",
        "company": "string",
        "url": "string",
        "description": "string",
        "location": "string"
      }
    ]
  }
  ```
- Auth: `X-Webhook-Secret` header validated against `WEBHOOK_SECRET` env var
- Orchestrator scores incoming jobs against current preferences; inserts matches into `jobs` table with `source: webhook`
- Deduplication: jobs with existing URL are skipped

**Frontend deliverables:**
- Settings page: displays webhook URL + secret
- Webhook-sourced jobs show "via webhook" badge in dashboard

**Integration contract:** External email-processing agents (out of scope) parse job alert emails and POST to this endpoint. The schema above is the stable interface.

**Success criteria:** External agent POSTs job alerts; matching jobs appear in dashboard within seconds.

---

## Error Handling

| Scenario | Behavior |
|---|---|
| SerpAPI quota / rate limit | Dashboard toast; scheduler backs off; jobs table untouched |
| Agent timeout / failure | Job/application marked `error` with `error_reason`; never silently dropped |
| Playwright form parse failure | Returns raw URL with `status: manual_required`; "Open manually" fallback shown |
| OAuth token expiry | Auto-refresh attempted; frontend prompts reconnect on failure |
| Duplicate webhook job | Silently deduplicated by URL; no error raised |

---

## Testing Strategy

- **Unit tests:** Each agent tool is a pure function testable in isolation with mocked API responses (SerpAPI fixtures, mock Playwright responses)
- **Agent integration tests:** Full agent loop tested with recorded fixtures (no live API calls in CI)
- **Frontend:** Component tests for ReviewPanel, JobCard with mock API responses

---

## Environment Variables

```bash
# LLM
ANTHROPIC_API_KEY=
ORCHESTRATOR_MODEL=claude-haiku-4-5        # swap to claude-sonnet-4-6 if needed
SCOUT_MODEL=claude-haiku-4-5
APPLICATOR_MODEL=claude-haiku-4-5
OUTREACH_MODEL=claude-haiku-4-5

# Job Discovery
SERP_API_KEY=
JOB_MATCH_THRESHOLD=0.6                    # minimum match score to store

# Email
EMAIL_PROVIDER=gmail                       # 'gmail' | 'outlook'
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REFRESH_TOKEN=
OUTLOOK_CLIENT_ID=
OUTLOOK_CLIENT_SECRET=
OUTLOOK_REFRESH_TOKEN=

# Webhook
WEBHOOK_SECRET=

# Database
DATABASE_URL=sqlite:///./jobapplier.db
```

---

## Out of Scope (Deferred)

- Multi-user authentication
- Full autonomous form submission (no human in the loop)
- Direct job board API integrations (LinkedIn, Indeed, Glassdoor) — SerpAPI used instead
- Board-specific scrapers
- Mobile app
