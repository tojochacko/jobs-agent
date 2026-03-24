# JobApplierAgent

An autonomous job search assistant that discovers matching jobs, pre-fills applications for supervised submission, sends cold outreach emails to HR contacts, and accepts job alerts from external agents via webhook. You retain final control over every form submission and email send.

## Features

- **Job Discovery** — Polls Google Jobs via SerpAPI on a configurable schedule (default every 6 hours) and scores each result against your preferences using Claude AI
- **Supervised Application Flow** — Pre-fills job application forms using Playwright; you review and submit manually (the agent never auto-submits)
- **Cold Email Outreach** — Finds HR contacts, drafts tailored cover letters, and attaches a customised PDF resume; you click Send
- **Webhook Ingestion** — Accepts job alerts from external agents (e.g. a Gmail-processing bot) via a signed `POST /webhook/job-alerts` endpoint
- **Dashboard** — React UI for browsing discovered jobs, tracking application pipeline, reviewing outreach history, and configuring settings

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + Vite (JavaScript) |
| Backend | Python 3.12 + FastAPI |
| LLM | LiteLLM — defaults to `anthropic/claude-haiku-4-5`; swap provider via env var |
| Job Discovery | SerpAPI (Google Jobs + Google Search) |
| Browser Automation | Playwright (supervised — never auto-submits) |
| Email | Gmail or Outlook via OAuth 2.0 |
| Database | SQLite via SQLAlchemy (PostgreSQL-compatible schema) |
| Scheduling | APScheduler |
| Package Management | uv (Python) · npm (Node) |
| Containerisation | Docker + Docker Compose |
| Testing | pytest (backend) · Vitest + Testing Library (frontend) |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- An [Anthropic API key](https://console.anthropic.com/) (or OpenAI / Gemini if using those providers via LiteLLM)
- A [SerpAPI key](https://serpapi.com/) (for job discovery)
- (Optional) Gmail or Outlook OAuth credentials for email outreach

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/JobApplierAgent.git
cd JobApplierAgent
```

### 2. Create your environment file

```bash
cp .env.example .env   # or create .env manually
```

Edit `.env` with your credentials:

```bash
# Required
ANTHROPIC_API_KEY=your-anthropic-api-key
SERP_API_KEY=your-serpapi-key

# Optional — LLM provider keys (only needed if using non-Anthropic models)
OPENAI_API_KEY=
GEMINI_API_KEY=

# Optional — LLM model overrides; prefix determines provider (defaults shown)
ORCHESTRATOR_MODEL=anthropic/claude-haiku-4-5
SCOUT_MODEL=anthropic/claude-haiku-4-5
APPLICATOR_MODEL=anthropic/claude-haiku-4-5
OUTREACH_MODEL=anthropic/claude-haiku-4-5

# Optional — Job filtering
JOB_MATCH_THRESHOLD=0.6          # minimum score to store a job (0.0–1.0)
WEBHOOK_BYPASS_THRESHOLD=false   # set true to store all webhook jobs regardless of score

# Optional — Webhook (for external agent integration)
WEBHOOK_SECRET=your-webhook-secret

# Optional — Email OAuth (choose one provider)
EMAIL_PROVIDER=gmail              # 'gmail' or 'outlook'
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
OUTLOOK_CLIENT_ID=
OUTLOOK_CLIENT_SECRET=
OAUTH_REDIRECT_URI=http://localhost:8000/auth/email/callback
```

### 3. Start the application

```bash
docker compose up --build
```

This starts:
- **Backend** at `http://localhost:8000` (FastAPI + SQLite)
- **Frontend** at `http://localhost:5173` (React + Vite)

Open `http://localhost:5173` in your browser.

### 4. Configure your preferences

Navigate to the **Preferences** page and set:
- Job titles you're targeting
- Preferred location and remote/hybrid preference
- Experience level and domain
- Preferred company sizes

Upload your master resume (PDF only, max 50 MB) — the agent will tailor it per application.

## Usage

### Job Discovery

Jobs are discovered automatically every 6 hours. Click **Refresh** on the Dashboard to trigger an immediate search. Each job is scored by Claude against your preferences; only jobs above `JOB_MATCH_THRESHOLD` appear.

### Applying to a Job

Click **Apply** on any job card. The agent:
1. Opens the application URL with Playwright
2. Scrapes the form fields
3. Fills them using your tailored resume

You review the pre-filled form and submit it yourself.

### Cold Email Outreach

Click **Email HR** on any job card. The agent:
1. Searches for the HR contact at the company
2. Drafts a personalised cover letter
3. Attaches a tailored PDF resume

You review the draft in the Outreach panel and click **Send**.

### Webhook Integration

External agents can POST job alerts directly to the system:

```bash
curl -X POST http://localhost:8000/webhook/job-alerts \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: your-webhook-secret" \
  -d '{
    "source": "my-email-agent",
    "jobs": [{
      "title": "Senior Python Engineer",
      "company": "Acme Corp",
      "url": "https://acme.com/jobs/123",
      "description": "Remote FastAPI role",
      "location": "Remote"
    }]
  }'
```

Jobs are scored, deduplicated by URL, and surfaced in the dashboard with a **via webhook** badge.

## Development

This project is set up for development inside a VS Code Dev Container.

### Using VS Code Dev Containers

1. Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
2. Open the project folder in VS Code
3. Click **Reopen in Container** when prompted

The container mounts the source with hot-reload on both `:8000` (backend) and `:5173` (frontend).

### Running tests

```bash
# Backend tests (uv sync adds dev deps to the venv first — they're excluded from the prod image)
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/ -v"

# Frontend tests
docker compose exec frontend npm run test:run

# Linting
docker compose exec backend ruff check .
docker compose exec frontend npm run lint
```

## Project Structure

```
JobApplierAgent/
├── backend/
│   ├── main.py              # FastAPI app entrypoint
│   ├── config.py            # Environment variable settings
│   ├── models.py            # SQLAlchemy ORM models
│   ├── scheduler.py         # APScheduler background polling
│   ├── agents/
│   │   ├── job_scout.py     # Discovers and scores jobs via SerpAPI + Claude
│   │   ├── applicator.py    # Pre-fills application forms via Playwright
│   │   ├── orchestrator.py  # Scores individual jobs for webhook ingestion
│   │   └── outreach.py      # Finds HR contacts and drafts cover letters
│   ├── routers/             # FastAPI route handlers
│   └── tools/               # Shared utilities (SerpAPI, email, resume, Playwright)
├── frontend/
│   └── src/
│       ├── pages/           # Dashboard, Applications, Outreach, Settings
│       ├── components/      # AppShell, TagInput, JobCard, ReviewPanel, OutreachPanel, StatusBadge
│       └── api/client.js    # Typed API client
├── backend/pyproject.toml   # Python dependencies (uv)
├── backend/uv.lock          # Deterministic lock file
├── .devcontainer/           # VS Code Dev Container config
├── docker-compose.yml
└── .env                     # Your credentials (not committed)
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes* | — | Anthropic API key (*required when using `anthropic/` models) |
| `OPENAI_API_KEY` | No | — | OpenAI API key (only if using `openai/` models) |
| `GEMINI_API_KEY` | No | — | Gemini API key (only if using `gemini/` models) |
| `SERP_API_KEY` | Yes | — | SerpAPI key for job search |
| `ORCHESTRATOR_MODEL` | No | `anthropic/claude-haiku-4-5` | LiteLLM model string for job scoring |
| `SCOUT_MODEL` | No | `anthropic/claude-haiku-4-5` | LiteLLM model string for job discovery |
| `APPLICATOR_MODEL` | No | `anthropic/claude-haiku-4-5` | LiteLLM model string for form filling |
| `OUTREACH_MODEL` | No | `anthropic/claude-haiku-4-5` | LiteLLM model string for email drafting |
| `JOB_MATCH_THRESHOLD` | No | `0.6` | Minimum match score to store a job |
| `WEBHOOK_BYPASS_THRESHOLD` | No | `false` | Store all webhook jobs regardless of score |
| `WEBHOOK_SECRET` | No | — | Secret for `X-Webhook-Secret` header auth |
| `EMAIL_PROVIDER` | No | `gmail` | `gmail` or `outlook` |
| `GMAIL_CLIENT_ID` | No | — | Google OAuth client ID |
| `GMAIL_CLIENT_SECRET` | No | — | Google OAuth client secret |
| `OUTLOOK_CLIENT_ID` | No | — | Microsoft OAuth client ID |
| `OUTLOOK_CLIENT_SECRET` | No | — | Microsoft OAuth client secret |
| `OAUTH_REDIRECT_URI` | No | `http://localhost:8000/auth/email/callback` | OAuth callback URL |
| `DATABASE_URL` | No | `sqlite:///./jobapplier.db` | SQLAlchemy database URL |
