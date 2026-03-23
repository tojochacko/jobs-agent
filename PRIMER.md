# JobApplierAgent — Session Primer

## What Was Done This Session (2026-03-23)

Implemented **Phase 3 — Cold Email Outreach** in full across 6 tasks on `main`.

| Task | What was built |
|---|---|
| 1 — OAuthToken + Outreach Models | `OAuthToken` and `Outreach` ORM models added to `backend/models.py` |
| 2 — HR Contact Finder Tool | `backend/tools/hr_finder.py` — `find_hr_contact()` via SerpAPI + Claude extraction; all tests properly mocked |
| 3 — OAuth Token Management + Auth Router | `backend/tools/email_tools.py` — `get_valid_token`, `send_email_gmail`, `send_email_outlook`, `send_email`; `backend/routers/auth.py` — `/auth/email/connect` + `/auth/email/callback`; deps: google-auth, msal |
| 4 — Outreach Agent | `backend/agents/outreach.py` — `run_outreach()` + `generate_cover_letter()`; orchestrates HR lookup → cover letter → tailored PDF resume |
| 5 — Outreach Router | `backend/routers/outreach.py` — POST/GET/PATCH `/outreach`, POST `/outreach/{id}/send`; error recovery: job set to `error` on agent or send failure |
| 6 — Frontend Outreach | `OutreachPanel.jsx`, `Outreach.jsx`, `Settings.jsx`; Email HR button wired in `JobCard.jsx`; routes in `App.jsx` |

**Test coverage:** 64 backend + 18 frontend = **82 tests, all passing** on `main`.

---

## Current State

| Phase | Status |
|---|---|
| 1 — Foundation Dashboard | ✅ Complete |
| 2 — Application Flow | ✅ Complete |
| 3 — Cold Email Outreach | ✅ Complete (merged this session) |
| 4 — Webhook Integration | 🔲 Planned |

**New files added this phase:**
```
backend/tools/hr_finder.py
backend/tools/email_tools.py
backend/routers/auth.py
backend/routers/outreach.py
backend/agents/outreach.py
backend/tests/test_hr_finder.py
backend/tests/test_email_tools.py
backend/tests/test_auth_router.py
backend/tests/test_outreach_agent.py
backend/tests/test_outreach_router.py
frontend/src/components/OutreachPanel.jsx
frontend/src/components/OutreachPanel.test.jsx
frontend/src/pages/Outreach.jsx
frontend/src/pages/Settings.jsx
```

**Modified files:**
```
backend/models.py        (OAuthToken, Outreach models added)
backend/main.py          (auth + outreach routers registered)
backend/requirements.txt (google-auth, google-auth-oauthlib, google-api-python-client, msal)
frontend/src/api/client.js           (5 new exports)
frontend/src/components/JobCard.jsx  (Email HR button wired, OutreachPanel inline)
frontend/src/App.jsx                 (/outreach and /settings routes added)
```

**Known technical debt (not blocking):**
- `datetime.utcnow()` deprecated in Python 3.12+ — affects models.py, email_tools.py, routers — cleanup pass needed
- `OutreachPanel` fires PATCH on every keystroke (no debounce) — consistent with ReviewPanel pattern, acceptable for now

---

## Recommended Next Steps

**Phase 4 — Webhook Integration** is next. Plan file: `docs/superpowers/plans/2026-03-22-phase4-webhook-integration.md`.

Key things to know going into Phase 4:
- Webhook endpoint: `POST /webhook/job-alerts` — receives job alerts from external agents
- Jobs received via webhook should be de-duplicated by URL
- `WEBHOOK_SECRET` env var for HMAC signature verification
- `WEBHOOK_BYPASS_THRESHOLD=true` allows jobs to bypass the `JOB_MATCH_THRESHOLD` score filter

Use `superpowers:subagent-driven-development` to execute Phase 4 task by task.
