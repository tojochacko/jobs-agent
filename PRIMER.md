# JobApplierAgent — Session Primer

## What Was Done This Session (2026-03-23, Phase 3 Task 4)

Implemented **Phase 3 Task 4 — Outreach Agent** using TDD on `main`.

| Step | What was done |
|---|---|
| Pre-read | Read `backend/tools/resume_tools.py` to verify `tailor_resume` signature and confirm `_read_resume` exists |
| Tests written | Created `backend/tests/test_outreach_agent.py` with 2 tests: happy-path draft return and unknown-contact fallback |
| Red phase | Confirmed `AttributeError: module 'backend.agents' has no attribute 'outreach'` for both tests |
| `outreach.py` implemented | Created `backend/agents/outreach.py` — `generate_cover_letter()` (reads resume, calls Claude with salutation) and `run_outreach()` (find HR → generate cover letter → tailor resume as PDF → return dict) |
| Key design | `tailor_resume(..., output_format="pdf")` returns `output_path`; `run_outreach` uses that return value as `resume_version_path` — matches what tests assert |
| File copy | Both files copied with `docker compose cp` (Docker doesn't volume-mount source code) |
| Green phase | 2 new tests pass; all 58 backend tests pass (0 failures) |
| Committed | `feat: add Outreach agent with cover letter and HR contact discovery` |

---

## Previous Session (2026-03-23, Phase 3 Task 3)

Implemented **Phase 3 Task 3 — OAuth Token Management + Auth Router** using TDD on `main`.

| Step | What was done |
|---|---|
| Dependencies installed | `google-auth`, `google-auth-oauthlib`, `google-api-python-client`, `msal` installed in container and added to `requirements.txt` |
| Tests written | Created `backend/tests/test_email_tools.py` (3 tests) and `backend/tests/test_auth_router.py` (2 tests) |
| Red phase | Confirmed `ModuleNotFoundError` for all 5 tests before implementation |
| `email_tools.py` implemented | `get_valid_token()` — loads token from DB, refreshes if expired, persists update; `send_email_gmail()`, `send_email_outlook()`, `send_email()` dispatch functions |
| `auth.py` router implemented | `POST /auth/email/connect` returns OAuth authorization URL; `GET /auth/email/callback` exchanges code, upserts `OAuthToken` in DB |
| `main.py` updated | `auth` router imported and registered with `app.include_router(auth.router)` |
| Note | Docker does not volume-mount source code; all files must be copied with `docker compose cp` |
| Green phase | All 5 new tests pass; all 56 backend tests pass (0 failures) |
| Committed | `feat: add OAuth token management and email send tools` |

---

## Previous Session (2026-03-23, Phase 3 Task 2)

Implemented **Phase 3 Task 2 — HR Contact Finder Tool** using TDD on `main`.

| Step | What was done |
|---|---|
| Tests written | Created `backend/tests/test_hr_finder.py` with 3 tests covering dict return shape, empty-results fallback, and search exception handling |
| Red phase | Confirmed `AttributeError` (module not found) for all 3 tests before implementation |
| Implementation | Created `backend/tools/hr_finder.py` — `find_hr_contact(company, job_title)` searches SerpAPI via `search_people`, feeds snippets to Claude (`OUTREACH_MODEL`) to extract name/email/confidence; falls back to `hr_confidence="unknown"` on any error (search or LLM) |
| serp.py verified | `search_people(query: str, num_results: int = 5)` — call signature confirmed before use |
| config.py verified | `settings.OUTREACH_MODEL` already present — no changes needed |
| Claude error handling | Added try/except around the Anthropic client call so tests without a real API key still pass |
| Green phase | All 3 new tests pass; all 51 backend tests pass |
| Committed | `feat: add HR contact finder tool via SerpAPI + Claude extraction` |

---

## Previous Session (2026-03-23, Phase 3 Task 1)

Implemented **Phase 3 Task 1 — OAuthToken and Outreach Models** using TDD on `main`.

| Step | What was done |
|---|---|
| Tests written | Added `test_create_oauth_token` and `test_create_outreach` to `backend/tests/test_models.py` |
| Red phase | Confirmed `ImportError` failures before adding models |
| Models added | `OAuthToken` and `Outreach` appended to `backend/models.py` |
| Green phase | All 7 model tests pass |
| Committed | `feat: add OAuthToken and Outreach models` |

---

## Previous Session (2026-03-23) — Phase 2 Complete

Implemented **Phase 2 — Supervised Application Flow** in full across 7 tasks on `feature/phase2-application-flow` (merged to `main`).

| Task | What was built |
|---|---|
| 1 — Resume Tailoring Tool | `backend/tools/resume_tools.py` — `tailor_resume()` with text/PDF modes, .txt/.pdf/.docx support, hardened error handling, optional `model` param |
| 2 — Playwright Tools | `backend/tools/playwright_tools.py` — `fetch_application_form()` + `open_prefilled_form()`; Dockerfile updated with Chromium system deps |
| 3 — Application Model | `Application` ORM model added to `backend/models.py` |
| 4 — Applicator Agent | `backend/agents/applicator.py` — `run_applicator()`: scrape form → tailor resume → LLM field mapping |
| 5 — Applications Router | `backend/routers/applications.py` — POST/GET/PATCH /applications + open-in-browser endpoint; error recovery sets job to `error` on agent failure |
| 6 — ReviewPanel + Apply Flow | `ReviewPanel.jsx`, Apply button wired in `JobCard.jsx`, error handling on all API calls |
| 7 — Applications Pipeline Page | `Applications.jsx` Kanban pipeline (4 stages), `/applications` route in `App.jsx` |

**Test coverage:** 46 backend + 16 frontend = **62 tests, all passing** on `main`.

---

## Current State

| Phase | Status |
|---|---|
| 1 — Foundation Dashboard | ✅ Complete |
| 2 — Application Flow | ✅ Complete (merged this session) |
| 3 — Cold Email Outreach | 🔄 In progress (Tasks 1–4 done) |
| 4 — Webhook Integration | 🔲 Planned |

**New files added this phase:**
```
backend/agents/applicator.py
backend/routers/applications.py
backend/tools/playwright_tools.py
backend/tools/resume_tools.py
frontend/src/pages/Applications.jsx
frontend/src/components/ReviewPanel.jsx
```

**Modified files:**
```
backend/models.py        (Application model added; OAuthToken + Outreach models added in Phase 3 Task 1)
backend/main.py          (applications router registered)
backend/Dockerfile       (Chromium system deps added)
backend/requirements.txt (fpdf2, pdfminer.six, python-docx, playwright added)
frontend/src/components/JobCard.jsx  (Apply button wired)
frontend/src/api/client.js           (4 new exports)
frontend/src/App.jsx                 (/applications route added)
```

---

## Recommended Next Steps

**Phase 3 — Cold Email Outreach** is next. Plan file: `docs/superpowers/plans/2026-03-22-phase3-cold-email-outreach.md`.

Key things to know going into Phase 3 Task 2+:
- `tailor_resume()` already supports `output_format="pdf"` for email attachments — pass `model=settings.OUTREACH_MODEL` from the Outreach agent
- `OAuthToken` and `Outreach` models are now in `models.py` — Task 1 complete
- OAuth tokens are stored in the DB (`oauth_tokens` table), not in `.env`
- Email provider selected via `EMAIL_PROVIDER` env var (`gmail` or `outlook`)
- `get_valid_token(provider, db)` is in `email_tools.py` — call this from Outreach agent before sending
- `send_email(to, subject, body, attachment_path, db)` is the top-level dispatch function (auto-selects Gmail/Outlook via `settings.EMAIL_PROVIDER`)
- Auth endpoints live at `POST /auth/email/connect` and `GET /auth/email/callback`
- Next task: Task 5 — Outreach Router

Use `superpowers:subagent-driven-development` to execute Phase 3 task by task.
