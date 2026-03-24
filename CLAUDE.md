# JobApplierAgent — Claude Code Guide

## Claude Behaviour Rules

- **Always research before responding.** Before describing project structure, commands, file paths, or tooling, read the actual files in the codebase. Never invent file names, commands, or configuration that have not been verified to exist. If uncertain, use Glob/Grep/Read tools to confirm first.
- **Write/update `PRIMER.md` after every session.** At the end of each conversation, write or update `PRIMER.md` in the project root with three sections: what was done this session, current state of the project, and recommended next steps. This keeps context continuity across sessions.

## Project Overview

JobApplierAgent is a single-user autonomous job search assistant. It discovers matching jobs, pre-fills applications for supervised submission, sends cold emails to HR contacts, and accepts job alerts from external agents via webhook. The user retains final control over every submission and send action.

## Tech Stack

| Layer | Choice |
|---|---|
| Frontend | React 19 + Vite (JavaScript) |
| Backend | Python 3.12 + FastAPI |
| LLM | `claude-haiku-4-5` for all agents (upgrade via `ORCHESTRATOR_MODEL` env var to `claude-sonnet-4-6`) |
| Job Discovery | SerpAPI (Google Jobs + Google Search) |
| Browser Automation | Playwright (supervised mode only — agent never auto-submits) |
| Email | Gmail / Outlook OAuth |
| Database | SQLite via SQLAlchemy (PostgreSQL-compatible schema) |
| Scheduling | APScheduler |
| Testing | pytest (backend), Vitest + Testing Library (frontend) |

## Project Structure

```
JobApplierAgent/
├── backend/
│   ├── main.py                   # FastAPI app entrypoint, lifespan, CORS
│   ├── config.py                 # Pydantic settings (env vars)
│   ├── database.py               # SQLAlchemy engine + session dependency
│   ├── models.py                 # ORM models: Preference, Resume, Job, Application, Outreach, OAuthToken
│   ├── scheduler.py              # APScheduler background polling
│   ├── agents/
│   │   ├── job_scout.py          # JobScout Agent (SerpAPI + scoring)
│   │   ├── applicator.py         # Applicator Agent (Playwright form pre-fill)
│   │   ├── orchestrator.py       # Orchestrator scoring agent (scores webhook jobs against preferences)
│   │   └── outreach.py           # Outreach Agent (HR contact + email)
│   ├── routers/
│   │   ├── preferences.py        # GET/POST /preferences
│   │   ├── jobs.py               # GET/DELETE /jobs, POST /jobs/refresh
│   │   ├── resume.py             # POST/GET /resume
│   │   ├── applications.py       # POST/GET/PATCH /applications
│   │   ├── outreach.py           # POST/GET/PATCH /outreach, POST /outreach/{id}/send
│   │   ├── auth.py               # POST /auth/email/connect, GET /auth/email/callback
│   │   └── webhook.py            # POST /webhook/job-alerts
│   ├── tools/
│   │   ├── serp.py               # SerpAPI wrapper (jobs + Google Search)
│   │   ├── playwright_tools.py   # Form scraping + supervised pre-fill
│   │   ├── email_tools.py        # Gmail/Outlook OAuth send + token management
│   │   ├── hr_finder.py          # HR contact lookup via SerpAPI + Claude extraction
│   │   └── resume_tools.py       # tailor_resume (shared: text for forms, pdf for email)
│   └── tests/                    # pytest tests (in-memory SQLite)
│
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.jsx     # Job discovery dashboard
│       │   ├── Preferences.jsx   # Job criteria + resume upload
│       │   ├── Applications.jsx  # Application pipeline tracker
│       │   ├── Outreach.jsx      # Cold email history
│       │   └── Settings.jsx      # Webhook URL/secret, email OAuth connect
│       ├── components/
│       │   ├── JobCard.jsx
│       │   ├── StatusBadge.jsx
│       │   ├── ReviewPanel.jsx   # Resume diff + form preview
│       │   └── OutreachPanel.jsx # HR contact + cover letter draft editor
│       ├── api/client.js         # Typed axios wrappers for all endpoints
│       └── App.jsx               # React Router setup
│
├── uploads/                      # Resume file storage (PDF/DOCX)
├── docs/superpowers/
│   ├── specs/                    # Design spec (source of truth)
│   └── plans/                    # Phase implementation plans
└── backend/jobapplier.db         # SQLite database
```

## Architecture

```
React Frontend (Vite @ :5173)
  └─ Proxied via Vite dev server → FastAPI Backend (:8000)
        ├─ REST API Routers
        │     ├─ JobScout Agent      (SerpAPI → Claude scoring)
        │     ├─ Applicator Agent    (Playwright → form pre-fill)
        │     ├─ Outreach Agent      (SerpAPI HR lookup → cover letter → email)
        │     └─ Orchestrator Agent  (scores webhook jobs against preferences)
        ├─ APScheduler (configurable interval, default 6h)
        └─ SQLite DB
```

## Docker Environment

**This project runs entirely inside Docker containers.**

- **Development:** VSCode Dev Containers (`.devcontainer/`). Open the project in VSCode and use "Reopen in Container" — this builds and attaches to the `backend` service with hot-reload and port forwarding for both `:8000` and `:5173`.
- **Production:** `docker compose up --build` using the root `docker-compose.yml`.

> **IMPORTANT for Claude:** Do NOT run host-level tooling commands such as `npm`, `pip`, `uv`, `ruff`, `uvicorn`, `pytest`, `node`, or any other package manager / runtime commands directly in the host shell. All such commands must be executed inside the appropriate container.

Run commands inside containers (when not using the devcontainer terminal):
```bash
docker compose exec backend pytest           # run backend tests
docker compose exec backend ruff check .     # lint backend
docker compose exec frontend npm run test:run  # run frontend tests
docker compose exec frontend npm run lint    # lint frontend
```

## Development Commands (inside containers)

**Backend:**
```
pip install -r requirements.txt
uvicorn main:app --reload          # starts at :8000
pytest                             # run all tests
```

**Frontend:**
```
npm install
npm run dev                        # starts Vite at :5173
npm run test:run                   # run tests once
npm run lint
```

## Environment Variables

```bash
# LLM
ANTHROPIC_API_KEY=
ORCHESTRATOR_MODEL=claude-haiku-4-5   # or claude-sonnet-4-6
SCOUT_MODEL=claude-haiku-4-5
APPLICATOR_MODEL=claude-haiku-4-5
OUTREACH_MODEL=claude-haiku-4-5

# Job Discovery
SERP_API_KEY=
JOB_MATCH_THRESHOLD=0.6               # minimum match score to store
WEBHOOK_BYPASS_THRESHOLD=false        # true = store all webhook jobs regardless of score

# Email
EMAIL_PROVIDER=gmail                  # 'gmail' | 'outlook'
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
OUTLOOK_CLIENT_ID=
OUTLOOK_CLIENT_SECRET=
OAUTH_REDIRECT_URI=http://localhost:8000/auth/email/callback

# Webhook
WEBHOOK_SECRET=

# Database
DATABASE_URL=sqlite:///./jobapplier.db
```

> OAuth tokens are stored in the `oauth_tokens` DB table, not in `.env`.

## Key Design Decisions

- **Human in the loop always:** The Applicator Agent never submits a form; the Outreach Agent never sends an email without the user clicking Send.
- **Job status lifecycle:** `new → saved | dismissed | applying | applied | emailing | emailed | error`
- **Application status lifecycle:** `pending → reviewing → submitted | rejected | interviewing | offered | manual_required`
- **Duplicate prevention:** `jobs.status` is set to `applying`/`emailing` immediately on trigger — UI disables those buttons if already in that state.
- **Playwright fallback:** If a form can't be parsed, `applications.status = 'manual_required'` and the raw URL is surfaced.
- **Match threshold:** Jobs scoring below `JOB_MATCH_THRESHOLD` (default 0.6) are not stored. Webhook jobs can bypass this with `WEBHOOK_BYPASS_THRESHOLD=true`.
- **tailor_resume shared tool:** Used by both Applicator (`output_format="text"` for form fields) and Outreach (`output_format="pdf"` for email attachment) — defined in `tools/resume_tools.py`.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET/POST | `/preferences` | Read or update job search criteria |
| POST | `/resume` | Upload master resume |
| GET | `/jobs` | List discovered jobs |
| GET | `/jobs/{id}` | Get single job detail |
| DELETE | `/jobs/{id}` | Dismiss a job |
| POST | `/jobs/refresh` | Manually trigger job scout poll |
| POST | `/applications` | Trigger application flow for a job |
| GET | `/applications` | List all applications |
| PATCH | `/applications/{id}` | Update status or notes |
| POST | `/outreach` | Trigger outreach flow for a job |
| GET | `/outreach` | List all outreach records |
| PATCH | `/outreach/{id}` | Edit draft (hr_name, hr_email, cover_letter only) |
| POST | `/outreach/{id}/send` | Send email; sole path to set status=sent |
| POST | `/auth/email/connect` | Initiate OAuth; returns provider auth URL |
| GET | `/auth/email/callback` | OAuth callback; exchanges code, writes tokens to DB |
| POST | `/webhook/job-alerts` | Receive job alerts from external agents |

## Implementation Phases

| Phase | Status | Scope |
|---|---|---|
| 1 — Foundation Dashboard | Complete | Backend API, JobScout Agent, scheduler, job dashboard, preferences, resume upload |
| 2 — Application Flow | Complete | Applicator Agent, Playwright form pre-fill, application tracking pipeline |
| 3 — Cold Email Outreach | Complete | Outreach Agent, Gmail/Outlook OAuth, HR contact lookup, cover letter generation |
| 4 — Webhook Integration | Complete | `POST /webhook/job-alerts`, Orchestrator scoring agent, external agent ingestion, deduplication |

## Testing Approach

- **Backend:** pytest with in-memory SQLite fixtures (`backend/tests/conftest.py`). Each agent tool is a pure function tested in isolation with mocked API responses. No live API calls in CI.
- **Frontend:** Vitest + jsdom. Component tests for JobCard, StatusBadge, ReviewPanel, OutreachPanel; page integration tests for Dashboard, Preferences, Applications; API client unit tests.
- Always add tests when implementing new agent tools or API endpoints.

## Error Handling Conventions

| Scenario | Behavior |
|---|---|
| SerpAPI quota/rate limit | Toast in dashboard; scheduler backs off; DB untouched |
| Agent timeout/failure | Job or application marked `error` with `error_reason`; never silently dropped |
| Playwright form parse failure | `applications.status = 'manual_required'`; "Open manually" fallback shown |
| OAuth token expiry | Auto-refresh; new token persisted to DB; frontend prompts reconnect if refresh fails |
| Duplicate webhook job | Silently deduplicated by URL |
| Duplicate Apply/Email HR | Blocked if `jobs.status` already `applying`, `applied`, `emailing`, or `emailed` |

## Out of Scope

- Multi-user authentication
- Full autonomous form submission (no human-in-the-loop bypass)
- Direct job board API integrations (LinkedIn, Indeed, Glassdoor) — SerpAPI only
- Mobile app
