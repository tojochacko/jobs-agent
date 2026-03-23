# JobApplierAgent — Session Primer

## What Was Done This Session (2026-03-23)

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
| 3 — Cold Email Outreach | 🔲 Planned |
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
backend/models.py        (Application model added)
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

Key things to know going into Phase 3:
- `tailor_resume()` already supports `output_format="pdf"` for email attachments — pass `model=settings.OUTREACH_MODEL` from the Outreach agent
- The `OAuthToken` model is referenced in CLAUDE.md but not yet in `models.py` — Phase 3 Task 1 must add it
- OAuth tokens are stored in the DB (`oauth_tokens` table), not in `.env`
- Email provider selected via `EMAIL_PROVIDER` env var (`gmail` or `outlook`)

Use `superpowers:subagent-driven-development` to execute Phase 3 task by task.
