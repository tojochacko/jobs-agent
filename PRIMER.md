# JobApplierAgent — Session Primer

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
  - Task 2 (Playwright Tools): Pending.
  - Task 3 (Application Model): Pending.
  - Task 4 (Applicator Agent): Pending.
  - Task 5 (Applications Router): Pending.
  - Task 6 (ReviewPanel + Apply Flow): Pending.
  - Task 7 (Applications Pipeline Page): Pending.
- **Phase 3 (Cold Email Outreach):** Planned.
- **Phase 4 (Webhook Integration):** Planned.
- Full backend test suite: 32 tests passing, no regressions.
- Active worktree: `/Users/tojochacko/code/JobApplierAgent/.worktrees/phase2-application-flow/` on branch `feature/phase2-application-flow`.

## Next Steps

- Phase 2 Task 2: Implement Playwright tools (`backend/tools/playwright_tools.py`) — form scraping and supervised pre-fill.
- Phase 2 Task 3: Add Application ORM model to `backend/models.py`.
- Phase 2 Task 4: Implement Applicator Agent (`backend/agents/applicator.py`).
- Phase 2 Task 5: Implement Applications Router (`backend/routers/applications.py`).
- Phase 2 Tasks 6–7: Frontend ReviewPanel component and Applications Pipeline page.
- Once Phase 2 is stable, begin Phase 3 (Outreach Agent, Gmail/Outlook OAuth, HR contact lookup, cover letter generation).
