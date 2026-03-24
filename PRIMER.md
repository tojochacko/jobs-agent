# JobApplierAgent — Session Primer

## What Was Done This Session (2026-03-24, continued)

Executed **Frontend UI Redesign** on branch `feat/frontend-ui-redesign`, then merged into `feat/litellm-migration`.

**Goal:** Apply a warm-neutral CSS theme, replace the top nav with a left sidebar, and upgrade the Preferences page with a tag input, dropdowns, and checkbox group.

| Task | Files changed | Result |
|---|---|---|
| 1 — CSS Theme | `frontend/src/App.css` | 13 CSS custom-property tokens + global resets (Vite starter removed) |
| 2 — AppShell | `AppShell.jsx`, `AppShell.css`, `App.jsx` | Left sidebar (172px, amber active state, 5 nav links via NavLink); routes wrapped in AppShell |
| 3 — TagInput (TDD) | `TagInput.jsx`, `TagInput.css`, `TagInput.test.jsx` | Controlled tag input; Enter/comma add; × and Backspace remove; duplicate suppression; id forwarding; 7 tests |
| 4 — Preferences | `Form.css`, `Preferences.jsx` | TagInput for job titles; dropdowns for experience (4 options) and domain (16 options); pill checkboxes for company size (6 options); Form.css shared styles |

**Branch:** `feat/litellm-migration` (contains both LiteLLM migration + UI redesign, not yet merged to `main`)

**Test count:** 75 backend + 25 frontend = **100 tests passing**

---

## What Was Done This Session (2026-03-24)

Executed **LiteLLM migration** across all 5 agent/tool files on branch `feat/litellm-migration`.

**Goal:** Replace the Anthropic SDK with LiteLLM so the LLM provider can be swapped via `ORCHESTRATOR_MODEL` / `SCOUT_MODEL` / `APPLICATOR_MODEL` / `OUTREACH_MODEL` env vars without touching code.

| Task | Files changed | Result |
|---|---|---|
| 1 — Swap dependency + config | `requirements.txt`, `config.py`, `test_config.py` | `litellm>=1.40.0` replaces `anthropic>=0.40.0`; model defaults prefixed `anthropic/`; `OPENAI_API_KEY` + `GEMINI_API_KEY` added as optional fields |
| 2 — orchestrator.py | `agents/orchestrator.py`, `tests/test_orchestrator.py` | `litellm.completion()` replaces `anthropic.Anthropic().messages.create()` |
| 3 — resume_tools.py | `tools/resume_tools.py`, `tests/test_resume_tools.py` | Same pattern swap |
| 4 — applicator.py | `agents/applicator.py`, `tests/test_applicator_agent.py` | Same pattern swap |
| 5 — outreach.py | `agents/outreach.py`, `tests/test_outreach_agent.py` | Same + new `test_generate_cover_letter_returns_string` test |
| 6 — job_scout.py | `agents/job_scout.py`, `tests/test_job_scout_agent.py` | Full tool use loop rewrite: Anthropic `stop_reason="tool_use"` + content blocks → OpenAI `finish_reason="tool_calls"` + `msg.tool_calls` list |
| 7 — Verification | — | 75 backend + 18 frontend tests all pass |

**Branch:** `feat/litellm-migration` (not yet merged to `main`)

**Test count:** 75 backend (74 baseline + 1 new) + 18 frontend = **93 tests passing**

**IMPORTANT — container rebuild needed:** `litellm` was installed via `pip install` directly into the running container during the session. Rebuild to persist it from `requirements.txt`:
```bash
docker compose up --build backend
```

---

## What Was Done Previously (2026-03-23)

Implemented **Phase 4 — Webhook Integration** in full across 2 tasks on `main`.

| Task | What was built |
|---|---|
| 1 — Orchestrator Scoring Agent | `backend/agents/orchestrator.py` — `score_job(job_data, preferences) -> float` using Claude Haiku; clamps to [0,1]; returns 0.0 on any error with warning log |
| 2 — Webhook Router | `backend/routers/webhook.py` — `POST /webhook/job-alerts`; validates `X-Webhook-Secret`; scores via orchestrator; respects `JOB_MATCH_THRESHOLD` + `WEBHOOK_BYPASS_THRESHOLD`; deduplicates by URL via `IntegrityError`; sets `source="webhook"`, `status="new"` |
| 3 — Settings verification | `frontend/src/pages/Settings.jsx` confirmed complete from Phase 3 (webhook URL + secret header shown) |

**Test coverage:** 74 backend + 18 frontend = **92 tests, all passing** on `main`.

**Phase 4 commits:**
- `2e3abaf` feat: add Orchestrator scoring agent for webhook job evaluation
- `70f719d` feat: add webhook endpoint for external job alert ingestion
- `2999403` fix: isolate WEBHOOK_SECRET in test_webhook_requires_secret
- `da4995f` fix: simplify exception clause, clarify bypass comment, add DB assertion to bypass test

---

## What Was Done Previously (2026-03-23, Phase 3)

Implemented **Phase 3 — Cold Email Outreach** in full across 6 tasks on `main`.

| Task | What was built |
|---|---|
| 1 — OAuthToken + Outreach Models | `OAuthToken` and `Outreach` ORM models added to `backend/models.py` |
| 2 — HR Contact Finder Tool | `backend/tools/hr_finder.py` — `find_hr_contact()` via SerpAPI + Claude extraction; all tests properly mocked |
| 3 — OAuth Token Management + Auth Router | `backend/tools/email_tools.py` — `get_valid_token`, `send_email_gmail`, `send_email_outlook`, `send_email`; `backend/routers/auth.py` — `/auth/email/connect` + `/auth/email/callback`; deps: google-auth, msal |
| 4 — Outreach Agent | `backend/agents/outreach.py` — `run_outreach()` + `generate_cover_letter()`; orchestrates HR lookup → cover letter → tailored PDF resume |
| 5 — Outreach Router | `backend/routers/outreach.py` — POST/GET/PATCH `/outreach`, POST `/outreach/{id}/send`; error recovery: job set to `error` on agent or send failure |
| 6 — Frontend Outreach | `OutreachPanel.jsx`, `Outreach.jsx`, `Settings.jsx`; Email HR button wired in `JobCard.jsx`; routes in `App.jsx` |

---

## Current State

| Phase | Status |
|---|---|
| 1 — Foundation Dashboard | ✅ Complete |
| 2 — Application Flow | ✅ Complete |
| 3 — Cold Email Outreach | ✅ Complete |
| 4 — Webhook Integration | ✅ Complete |

**All phases complete. Full system operational.**

**New files added in Phase 4:**
```
backend/agents/orchestrator.py
backend/tests/test_orchestrator.py
backend/routers/webhook.py
backend/tests/test_webhook_router.py
```

**Modified files in Phase 4:**
```
backend/main.py   (webhook router registered)
```

**Known technical debt (not blocking):**
- `datetime.utcnow()` deprecated in Python 3.12+ — affects `models.py`, `email_tools.py`, routers — cleanup pass needed
- `OutreachPanel` fires PATCH on every keystroke (no debounce) — consistent with ReviewPanel pattern, acceptable for now
- `jobs.url` has both column-level `unique=True` and a named `UniqueConstraint` in `__table_args__` — harmless for SQLite, would create duplicate constraints on PostgreSQL

---

## Recommended Next Steps

All four planned phases are complete. The full system is ready to use:

```bash
# Start backend (inside devcontainer or via docker compose)
uvicorn main:app --reload --port 8000

# Start frontend
npm run dev
```

**Potential follow-up improvements:**
- Merge `feat/litellm-migration` to `main` after manual verification (contains both LiteLLM + UI redesign)
- Fix `datetime.utcnow()` deprecation warnings across the codebase
- Upgrade webhook auth to HMAC-SHA256 signature verification (currently simple string equality)
- Add a startup warning log when `WEBHOOK_SECRET` is not configured
- Add payload schema display to the Settings page for external agent developer reference
- Add async/batch scoring to webhook router for large job payloads
- Restyle Dashboard, Applications, Outreach, Settings page internals (currently have inline styles; left out of scope this phase)
