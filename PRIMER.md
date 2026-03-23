# JobApplierAgent — Session Primer

## What Was Done (2026-03-23, Session 4)

- Implemented **Task 4 of Phase 2**: the Applicator Agent (`backend/agents/applicator.py`).
  - `run_applicator(job_id, job_url, job_description, resume_path)` orchestrates three steps: form scraping via `fetch_application_form`, resume tailoring via `tailor_resume` (text format), and LLM field mapping via `anthropic.Anthropic.messages.create`.
  - Returns `{"status": "ready", "form_payload": {...}, "tailored_resume": "...", "form_fields": [...], "url": ...}` on success.
  - Returns `{"status": "manual_required", "url": ...}` if form scraping fails, resume tailoring raises, or the LLM call raises.
  - Handles malformed JSON from the LLM gracefully — logs a warning and returns `form_payload: {}` instead of crashing.
- Added 3 TDD tests in `backend/tests/test_applicator_agent.py` covering: happy path, form scraping failure, and invalid LLM JSON.
- Full backend test suite: **38 tests passing**, no regressions.
- Committed as `feat: add Applicator agent with form scraping and resume tailoring` on branch `feature/phase2-application-flow`.

## What Was Done (2026-03-23, Session 3)

- Implemented **Task 2 of Phase 2**: Playwright form scraping and supervised prefill tools (`backend/tools/playwright_tools.py`).
  - `fetch_application_form(url)`: launches headless Chromium, navigates to the URL, scrapes all `input`/`textarea`/`select` elements, excludes `file`/`hidden`/`submit`/`button` type inputs, returns `{"fields": [...], "title": ..., "url": ...}`. On any exception, returns `{"status": "manual_required", "url": ..., "error": ...}`.
  - `open_prefilled_form(url, payload)`: opens a non-headless browser, navigates to the URL, fills each field using `[name='...'], [id='...']` locators, then blocks on `input()` so the user can submit manually before the browser closes.
- Added `playwright>=1.48.0` to `backend/requirements.txt`.
- Updated `backend/Dockerfile` to install Chromium system packages (`chromium`, `chromium-driver`, `libnss3`, etc.) and set `PLAYWRIGHT_BROWSERS_PATH`/`PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD` env vars so Playwright uses system Chromium.
- Added 2 TDD tests in `backend/tests/test_playwright_tools.py` — all passing.
- Full backend test suite: 34 tests passing (up from 32), no regressions.
- Committed as `feat: add Playwright form scraping and supervised prefill tools` on branch `feature/phase2-application-flow`.

## What Was Done (2026-03-23, Session 2)

- Implemented **Task 1 of Phase 2**: the shared resume tailoring tool (`backend/tools/resume_tools.py`).
  - Added `tailor_resume()`, `_read_resume()`, and `_write_pdf()` functions.
  - `_read_resume()` supports `.txt`, `.pdf` (via pdfminer.six), and `.docx`/`.doc` (via python-docx).
  - `_write_pdf()` uses fpdf2 to write tailored resume text as a PDF.
  - `tailor_resume()` calls the Anthropic API (model from `settings.APPLICATOR_MODEL`) and returns either plain text or a PDF path.
- Added 3 TDD tests in `backend/tests/test_resume_tools.py` — all passing (32/32 full suite).
- Added `fpdf2==2.7.9`, `pdfminer.six==20231228`, `python-docx==1.1.2` to `backend/requirements.txt`.
- Committed as `feat: add shared resume tailoring tool` on branch `feature/phase2-application-flow`.

## What Was Done (2026-03-23, Session 1)

- Added a **Docker Environment** section to `CLAUDE.md` documenting that the project uses Docker containers for both dev and production.
- Corrected a hallucinated `docker-compose.dev.yml` command — confirmed via codebase research that development uses **VSCode Dev Containers** (`.devcontainer/devcontainer.json` + `.devcontainer/docker-compose.yml`), not a separate compose file.
- Added a **Claude Behaviour Rules** section to `CLAUDE.md` with two rules:
  1. Always research the codebase before responding — never invent file names, commands, or config.
  2. Write/update `PRIMER.md` at the end of every session.
- Created persistent memory entry `feedback_research_before_responding.md` to reinforce the research-first rule across sessions.

## Current State

- **Phase 1 (Foundation Dashboard):** Complete — backend API, JobScout Agent, scheduler, job dashboard, preferences, resume upload all implemented.
- **Phase 2 (Application Flow):** In progress.
  - Task 1 (Resume Tailoring Tool): DONE — `backend/tools/resume_tools.py` committed.
  - Task 2 (Playwright Tools): DONE — `backend/tools/playwright_tools.py` committed.
  - Task 3 (Application Model): DONE — `Application` ORM model in `backend/models.py` committed.
  - Task 4 (Applicator Agent): DONE — `backend/agents/applicator.py` committed.
  - Task 5 (Applications Router): Pending.
  - Task 6 (ReviewPanel + Apply Flow): Pending.
  - Task 7 (Applications Pipeline Page): Pending.
- **Phase 3 (Cold Email Outreach):** Planned.
- **Phase 4 (Webhook Integration):** Planned.
- Full backend test suite: 38 tests passing, no regressions.
- Active worktree: `/Users/tojochacko/code/JobApplierAgent/.worktrees/phase2-application-flow/` on branch `feature/phase2-application-flow`.

## Next Steps

- Phase 2 Task 5: Implement Applications Router (`backend/routers/applications.py`).
- Phase 2 Tasks 6–7: Frontend ReviewPanel component and Applications Pipeline page.
- Once Phase 2 is stable, begin Phase 3 (Outreach Agent, Gmail/Outlook OAuth, HR contact lookup, cover letter generation).
