# JobApplierAgent — Session Primer

## What Was Done This Session (2026-03-25)

### JobScout Refactor — Fetch-First Pattern

Replaced the agentic tool-call loop in `backend/agents/job_scout.py` with a simpler fetch-first design:
- SerpAPI is now called directly by `run_job_scout()` once per job title
- A single LLM call handles scoring only (no tools passed)
- Scoring prompt rewritten to be explicit about its role (judge, not searcher)
- 6 new tests replace the old tool-call-based tests; all pass

**Key learning:** The tool-call loop added no quality value here — the LLM was just mechanically echoing `job_titles` into search queries. The real LLM value is in scoring. Agentic loops are justified only when the LLM needs to make non-deterministic decisions about which tools to call or how to adapt based on intermediate results.

### SerpAPI Remote Filter Fix

`backend/tools/serp.py` — passing `location="Remote"` to the `google_jobs` engine returned HTTP 400. Google Jobs does not accept "Remote" as a geographic location. Fix: detect `location.strip().lower() == "remote"` and pass `ltype=1` instead (Google Jobs native remote filter). Non-remote locations pass through as before.

### Deprecation Warning Fixes (Partial)

- `backend/routers/jobs.py` — `class Config: from_attributes = True` → `model_config = ConfigDict(from_attributes=True)` (Pydantic v2)
- `datetime.utcnow()` warnings in `auth.py`, `email_tools.py`, `outreach.py` — **intentionally left as `utcnow()` with `# noqa: DTZ003`**

**Key learning:** Replacing `datetime.utcnow()` with `datetime.now(timezone.utc)` breaks SQLite compatibility. SQLite stores datetimes as naive strings; SQLAlchemy returns naive datetimes on read. Comparing a timezone-aware datetime against a naive one raises `TypeError` at runtime, which caused `test_callback_stores_token` to hang. The correct fix requires migrating `OAuthToken.expires_at` to a timezone-aware column type — a schema migration, not a one-line swap.

### Docker + Test Workflow Learnings

- **Use `docker compose exec` not `run --rm`** for test runs when the stack is up. `run --rm` spawns a fresh container each time, accumulates OOM-killed containers, and causes severe resource contention (89 tests took 52 minutes under contention vs. seconds on a clean container).
- **Use the Agent tool for test runs and research** to avoid polluting the main context window with large output.
- **`uv add` requires a source volume mount** to persist `pyproject.toml`/`uv.lock` changes to the host. Use: `docker run --rm -v "$(pwd)/backend:/app" -w /app jobapplieragent-backend uv add <package>`

---

### OpenAI Provider Support Added to `backend/llm.py`

Added an OpenAI adapter to the in-house LLM gateway so agents can be configured to use OpenAI models via the `openai/` provider prefix.

**Changes:**
- `backend/llm.py` — added `import openai`, `case "openai":` branch in the `complete()` router, and `_openai_complete()` adapter. Messages pass through as-is (already in OpenAI format); tool call arguments are JSON-decoded from the response string.
- `backend/pyproject.toml` + `uv.lock` — `openai>=2.29.0` added as a dependency (resolved to `2.29.0`).
- `backend/tests/test_llm.py` — 3 new tests: `test_complete_openai_simple_text`, `test_complete_openai_tool_use`, `test_complete_openai_system_message_stays_in_messages`. All 11 llm tests pass.
- `.env` — corrected `gpt-5-mini` → `gpt-4o-mini` (the correct OpenAI model name).

**Note on `uv add` in Docker:** The production image has no source volume mount. To add packages and persist `pyproject.toml`/`uv.lock` changes, use: `docker run --rm -v "$(pwd)/backend:/app" -w /app jobapplieragent-backend uv add <package>`

---

### LLM Gateway Replacement (litellm → in-house `backend/llm.py`)

Replaced `litellm==1.82.6` with an in-house LLM gateway module. This was the planned follow-up to the prior session's supply chain attack mitigation (pinning litellm to 1.82.6). The new gateway eliminates the dependency entirely.

**New file: `backend/llm.py`**
- `complete(model, messages, max_tokens, tools) -> LLMResponse` — single entry point for all LLM calls
- `LLMResponse(content, tool_calls)` and `ToolCall(id, name, arguments)` dataclasses
- Dispatches on `provider/model` prefix; raises `ValueError` for unknown providers or missing `/`
- Anthropic adapter: extracts system messages, merges consecutive tool results, translates OpenAI-format `tool_calls` to Anthropic `tool_use` blocks
- `backend/tests/test_llm.py` — 8 unit tests covering all translation paths

**Migrated callers (6 files):**
- `backend/agents/orchestrator.py` — `response.choices[0].message.content` → `response.content`
- `backend/agents/applicator.py` — same pattern
- `backend/agents/outreach.py` — same pattern
- `backend/agents/job_scout.py` — agentic loop rewritten: checks `response.tool_calls` instead of `finish_reason == "tool_calls"`; reconstructs messages using `ToolCall` fields
- `backend/tools/hr_finder.py` — same pattern
- `backend/tools/resume_tools.py` — same pattern

**Dependency change:**
- `litellm` removed from `backend/pyproject.toml` and `backend/uv.lock`
- `anthropic>=0.40.0` added (resolved to `0.86.0` in lock file)

**Test suite:** 83/83 passing. All test files updated to mock `llm.complete` with `LLMResponse` instances.

---

---

## What Was Done This Session (2026-03-25, test performance)

### Test Suite: 47 Minutes → 0.67 Seconds

Diagnosed and fixed the test suite running at 47 minutes for 89 tests.

**Root cause:** `TestClient(app)` lifespan called `run_poll()` on every test. `run_poll()` queries the production SQLite DB (`/app/data/jobapplier.db`) which had real preferences saved — triggering live SerpAPI + OpenAI API calls (~90s each). With ~20 tests using the `client` fixture, that was ~30 minutes of live API calls in test setup alone.

**Fixes in `backend/tests/conftest.py`:**
- `db_engine` → `scope="session"` — `Base.metadata.create_all/drop_all` now runs once per session, not per test
- `client` → `scope="module"` — `TestClient` ASGI lifespan runs once per test module (8×) instead of per test
- Added `patch("backend.main.run_poll")` inside the `client` fixture — prevents real API calls during lifespan startup regardless of what's in the production DB
- Added `autouse=True` `clean_db` fixture — DELETEs all table rows after each test for isolation (replaces per-test schema rebuild)
- Removed `inspect()` assertions in conftest — were defensive guards that added reflection overhead per test
- `test_models.py` local `db` fixture replaced with shared `db_session` from conftest

**Fixes in test files (13 files):** Moved `from backend.x import y` from inside test functions to module level.

**Key discovery:** The Docker production container has NO source code bind mount. File edits on the host are not picked up by `docker compose exec`. Changes must be copied with `docker cp backend/tests/. <container>:/app/backend/tests/` until the image is rebuilt.

---

## Current State of the Project

All 7 implementation phases complete:

| Phase | Status | Scope |
|---|---|---|
| 1 — Foundation Dashboard | Complete | Backend API, JobScout Agent, scheduler, job dashboard |
| 2 — Application Flow | Complete | Applicator Agent, Playwright form pre-fill |
| 3 — Cold Email Outreach | Complete | Outreach Agent, Gmail/Outlook OAuth |
| 4 — Webhook Integration | Complete | POST /webhook/job-alerts, Orchestrator scoring |
| 5 — LiteLLM + UI Redesign | Complete | LiteLLM migration, warm-neutral CSS, AppShell |
| 6 — Security + uv Migration | Complete | Docker port hardening, pip → uv |
| 7 — LLM Gateway Replacement | Complete | litellm removed, in-house backend/llm.py |

**89 tests pass in 0.67s. No litellm references anywhere in the codebase. OpenAI and Anthropic providers both supported.**

---

## Recommended Next Steps

1. **Add a third LLM provider** — `backend/llm.py` supports `anthropic/` and `openai/`. Adding Gemini requires a `_gemini_complete()` adapter and `google-generativeai` dependency.
2. **Fix pre-existing deprecation warnings** — 55 warnings in the test suite:
   - `PydanticDeprecatedSince20` in `routers/jobs.py:12` — switch to `model_config = ConfigDict(...)`
   - `datetime.utcnow()` in `routers/auth.py`, `tools/email_tools.py`, `routers/outreach.py` — switch to `datetime.now(datetime.UTC)`
3. **Production smoke test** — start the stack with `docker compose up --build` and verify all agents can reach the Anthropic API end-to-end with a real `ANTHROPIC_API_KEY`.
