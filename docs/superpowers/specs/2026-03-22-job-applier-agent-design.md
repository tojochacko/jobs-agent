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
| Job Discovery | SerpAPI (Google Jobs endpoint for job search; Google Search endpoint for HR contact lookup) |
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
| Applicator | haiku-4-5 | Scrapes career forms, tailors resume for submission, pre-fills fields | `fetch_application_form`, `tailor_resume` |
| Outreach | haiku-4-5 | Finds HR contact, drafts cover letter, tailors resume as attachment, sends email | `find_hr_contact`, `generate_cover_letter`, `tailor_resume`, `send_email` |

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
    filepath TEXT NOT NULL,       -- path to file on disk (PDF or DOCX)
    uploaded_at TIMESTAMP
);

-- OAuth tokens (persisted across restarts; refreshed on expiry)
CREATE TABLE oauth_tokens (
    id INTEGER PRIMARY KEY,
    provider TEXT NOT NULL,       -- 'gmail' | 'outlook'
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

-- Discovered jobs
-- status lifecycle: new → saved | dismissed | applying | applied | emailing | emailed | error
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    description TEXT,
    location TEXT,
    match_score REAL,
    source TEXT NOT NULL,         -- 'serpapi' | 'webhook'
    status TEXT DEFAULT 'new',    -- 'new' | 'saved' | 'dismissed' | 'applying' | 'applied' | 'emailing' | 'emailed' | 'error'
    error_reason TEXT,
    created_at TIMESTAMP
);

-- Application tracking
-- status lifecycle: pending → reviewing → submitted | rejected | interviewing | offered
-- applied_at is NULL until the user confirms manual submission in the browser
CREATE TABLE applications (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    tailored_resume_path TEXT,    -- path to tailored resume file on disk
    form_payload JSON,
    status TEXT DEFAULT 'pending', -- 'pending' | 'reviewing' | 'submitted' | 'rejected' | 'interviewing' | 'offered' | 'manual_required'
    notes TEXT,
    applied_at TIMESTAMP          -- NULL until user confirms submission
);

-- Outreach tracking
CREATE TABLE outreach (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    hr_name TEXT,
    hr_email TEXT,
    hr_confidence TEXT,           -- 'search_result' | 'inferred_pattern' | 'unknown'
    cover_letter TEXT,
    resume_version_path TEXT,     -- path to tailored resume file used as attachment
    status TEXT DEFAULT 'draft',  -- 'draft' | 'sent'
    sent_at TIMESTAMP             -- NULL until email is sent
);
```

### Dashboard Status Mapping

The frontend pipeline view maps `jobs.status` and `applications.status` as follows:

| Pipeline Stage | Condition |
|---|---|
| **Discovered** | `jobs.status IN ('new', 'saved')` |
| **Reviewing** | `applications.status = 'reviewing'` |
| **Manual Required** | `applications.status = 'manual_required'` (Playwright could not parse form; user opens raw URL) |
| **Applied** | `applications.status = 'submitted'` OR `jobs.status = 'applied'` |
| **Response** | `applications.status IN ('rejected', 'interviewing', 'offered')` |

When a user clicks Apply, `jobs.status` transitions to `applying` immediately (prevents duplicate flows). On submission confirmation, both `jobs.status → applied` and `applications.status → submitted` are set together. The same pattern applies for email outreach: `jobs.status → emailing` on trigger, `→ emailed` on send.

---

## Shared Tool Interface

### `tailor_resume`

Used by both `Applicator` and `Outreach` agents. The output format differs by use case:

```python
def tailor_resume(
    job_description: str,
    master_resume_path: str,
    output_format: Literal["text", "pdf"],  # "text" for form fields; "pdf" for email attachment
    output_path: str                         # destination path; used only when output_format="pdf"
) -> str:
    # output_format="text": returns the tailored resume as a plain text string (output_path ignored)
    # output_format="pdf": writes a PDF to output_path and returns output_path
```

Both agents call the same function from `tools/resume_tools.py`. The `Applicator` passes `output_format="text"` and receives the tailored resume content as a string, which it uses directly to populate form fields. The `Outreach` agent passes `output_format="pdf"` and receives the path to a written PDF file, which it attaches to the email.

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
│       │   ├── Outreach.jsx         # Cold email history
│       │   └── Settings.jsx         # Webhook URL/secret, email OAuth connect
│       ├── components/
│       │   ├── JobCard.jsx
│       │   ├── ReviewPanel.jsx      # Resume diff + form preview / email draft
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
│   │   ├── serp.py                  # SerpAPI wrapper (jobs + search)
│   │   ├── playwright_tools.py      # Form scraping + supervised prefill
│   │   ├── email_tools.py           # Gmail/Outlook OAuth + send (reads tokens from DB)
│   │   └── resume_tools.py          # tailor_resume (shared, text + pdf output)
│   ├── scheduler.py                 # APScheduler setup
│   ├── models.py                    # SQLAlchemy models
│   ├── webhook.py                   # POST /webhook/job-alerts
│   └── config.py                    # Env vars, model config
│
├── uploads/                         # Resume file storage
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
- `JobScout Agent` with `search_jobs(query, location, filters) -> list[JobResult]` tool backed by SerpAPI Google Jobs endpoint
- APScheduler running JobScout on configurable interval (default: 6 hours); **runs an immediate poll on startup** so the dashboard is populated without waiting for the first interval
- SQLite schema: `preferences`, `resume`, `jobs` tables
- Match scoring: Haiku scores each SerpAPI result against user preferences (0.0–1.0); jobs below `JOB_MATCH_THRESHOLD` are not stored

**Frontend deliverables:**
- Preferences form (job titles, location, remote/hybrid, experience level, domain, company size, poll interval)
- Resume upload (PDF/DOCX accepted; stored to `uploads/` directory)
- Job dashboard: card/table view with match score, JD preview, source badge, action buttons (Apply / Email HR — disabled until Phase 2/3)
- Manual "Refresh Now" trigger for job polling

**Success criteria:** User configures criteria, uploads resume, sees a populated dashboard of relevant jobs within one poll cycle.

---

### Phase 2 — Supervised Application Flow

**Scope:** Applicator Agent, AI resume tailoring, Playwright supervised pre-fill, application tracking.

**Backend deliverables:**
- `Applicator Agent` with tools:
  - `fetch_application_form(url: str) -> FormSchema` — Playwright scrapes form fields; returns field list
  - `tailor_resume(job_description, master_resume_path, output_format="text", output_path) -> str` — Haiku tailors resume text for form fields
- `POST /applications` body: `{ "job_id": int }` — triggers applicator flow; sets `jobs.status = 'applying'`
- `GET /applications` — returns all applications with related job data
- `PATCH /applications/{id}` body: `{ "status": str, "notes": str }` — user updates status (e.g. marks as submitted after browser action); on `status=submitted` also sets `jobs.status = 'applied'` and `applications.applied_at = now()`
- `applications` table
- Fallback: if Playwright cannot parse the form, return `applications.status = 'manual_required'` with the raw URL

**Frontend deliverables:**
- "Apply" button triggers applicator flow with loading state
- Review panel: side-by-side tailored resume diff vs master + prefilled form fields preview
- "Open in Browser" button — Playwright opens pre-filled form for user final submit
- "Mark as Submitted" button — user confirms submission; calls `PATCH /applications/{id}` with `status=submitted`
- Application pipeline tab using the status mapping defined in the Data Model section

**Key constraint:** Agent never submits a form. It always stops at pre-fill and hands off.

**Success criteria:** User clicks Apply, reviews tailored resume + pre-filled form, opens in browser, submits manually, marks as submitted. Pipeline reflects correct stage.

---

### Phase 3 — Cold Email Outreach

**Scope:** Outreach Agent, Gmail/Outlook OAuth, HR contact discovery, AI cover letter generation, email review and send.

**Backend deliverables:**
- `Outreach Agent` with tools:
  - `find_hr_contact(company: str, job_title: str) -> HRContact` — SerpAPI Google Search queries for recruiter/hiring manager name and email on LinkedIn public profiles and company pages; returns `{ name, email, confidence: 'search_result' | 'inferred_pattern' | 'unknown' }`
  - `generate_cover_letter(job_description: str, master_resume_path: str, company: str) -> str`
  - `tailor_resume(job_description, master_resume_path, output_format="pdf", output_path) -> str`
  - `send_email(to: str, subject: str, body: str, attachment_path: str) -> bool` — reads OAuth tokens from `oauth_tokens` DB table; auto-refreshes and persists updated tokens on expiry
- Gmail OAuth via Google API (`gmail.send` scope); Outlook OAuth via Microsoft Graph (`Mail.Send` scope); provider chosen via `EMAIL_PROVIDER` env var
- **OAuth tokens stored in `oauth_tokens` DB table**, not in `.env` — tokens are refreshed and persisted to DB on each rotation. Initial setup flow:
  1. Frontend calls `POST /auth/email/connect` → backend returns a provider authorization URL
  2. Frontend opens that URL in a new tab; user grants permission
  3. Provider redirects to `GET /auth/email/callback?code=...`; backend exchanges code for tokens and writes to `oauth_tokens` table
  4. Callback returns success; frontend tab closes. `OAUTH_REDIRECT_URI` (e.g. `http://localhost:8000/auth/email/callback`) must be registered in the provider's app console and set in `.env`
- `POST /outreach` body: `{ "job_id": int }` — triggers outreach flow; sets `jobs.status = 'emailing'`
- `GET /outreach` — returns all outreach records
- `PATCH /outreach/{id}` body: `{ "hr_name": str, "hr_email": str, "cover_letter": str }` — user edits draft content only; `status` is not settable via PATCH (it transitions to `'sent'` exclusively via `POST /outreach/{id}/send`)
- Sending: `POST /outreach/{id}/send` — dispatches email; sets `outreach.status = 'sent'`, `outreach.sent_at = now()`, `jobs.status = 'emailed'`
- `outreach` table

**Frontend deliverables:**
- "Email HR" button triggers outreach flow; sets job to `emailing` state
- Review panel: HR contact (name, email, confidence badge), editable cover letter body, resume attachment preview
- Send button — calls `POST /outreach/{id}/send`
- Reconnect prompt if OAuth refresh fails (links to `POST /auth/email/connect`)
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
- Orchestrator scores incoming jobs against current preferences using the same `JOB_MATCH_THRESHOLD`; webhook jobs that score below threshold are not stored. Set `WEBHOOK_BYPASS_THRESHOLD=true` to store all webhook jobs regardless of score (useful when the sending agent has already pre-filtered)
- Deduplication: jobs with an existing URL are silently skipped

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
| Playwright form parse failure | `applications.status = 'manual_required'`; "Open manually" fallback shown in UI |
| OAuth token expiry | Auto-refresh attempted; updated token persisted to `oauth_tokens` table; frontend prompts reconnect if refresh fails |
| Duplicate webhook job | Silently deduplicated by URL; no error raised |
| Duplicate Apply / Email HR trigger | Blocked if `jobs.status` is already `applying`, `applied`, `emailing`, or `emailed`; UI disables buttons accordingly |

---

## Testing Strategy

- **Unit tests:** Each agent tool is a pure function testable in isolation with mocked API responses (SerpAPI fixtures, mock Playwright responses)
- **Agent integration tests:** Full agent loop tested with recorded fixtures (no live API calls in CI)
- **Frontend:** Component tests for ReviewPanel, JobCard with mock API responses

---

## API Endpoint Summary

| Method | Path | Description |
|---|---|---|
| GET/POST | `/preferences` | Read or update user job criteria |
| POST | `/resume` | Upload master resume |
| GET | `/jobs` | List discovered jobs (includes full description and match score) |
| GET | `/jobs/{id}` | Get full detail for a single job |
| DELETE | `/jobs/{id}` | Dismiss a job |
| POST | `/applications` | Trigger application flow for a job |
| GET | `/applications` | List all applications |
| PATCH | `/applications/{id}` | Update application status or notes |
| POST | `/outreach` | Trigger outreach flow for a job |
| GET | `/outreach` | List all outreach records |
| PATCH | `/outreach/{id}` | Edit outreach draft fields (hr_name, hr_email, cover_letter only) |
| POST | `/outreach/{id}/send` | Send the drafted email; sole path to set status=sent |
| POST | `/auth/email/connect` | Initiate OAuth flow; returns provider authorization URL |
| GET | `/auth/email/callback` | OAuth callback; exchanges code for tokens, writes to DB |
| POST | `/webhook/job-alerts` | Receive job alerts from external agents |

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
JOB_MATCH_THRESHOLD=0.6                    # minimum match score to store (applies to SerpAPI and webhook jobs)
WEBHOOK_BYPASS_THRESHOLD=false             # set true to store all webhook jobs regardless of score

# Email
EMAIL_PROVIDER=gmail                       # 'gmail' | 'outlook'
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
OUTLOOK_CLIENT_ID=
OUTLOOK_CLIENT_SECRET=
OAUTH_REDIRECT_URI=http://localhost:8000/auth/email/callback
# Note: access/refresh tokens are stored in the oauth_tokens DB table, not here

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
