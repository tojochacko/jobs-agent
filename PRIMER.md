# JobApplierAgent — Session Primer

## What Was Done This Session (2026-03-25)

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

**11 llm tests + full suite passing. No litellm references anywhere in the codebase. OpenAI and Anthropic providers both supported.**

---

## Recommended Next Steps

1. **Add a third LLM provider** — `backend/llm.py` supports `anthropic/` and `openai/`. Adding Gemini requires a `_gemini_complete()` adapter and `google-generativeai` dependency.
2. **Fix pre-existing deprecation warnings** — 55 warnings in the test suite:
   - `PydanticDeprecatedSince20` in `routers/jobs.py:12` — switch to `model_config = ConfigDict(...)`
   - `datetime.utcnow()` in `routers/auth.py`, `tools/email_tools.py`, `routers/outreach.py` — switch to `datetime.now(datetime.UTC)`
3. **Production smoke test** — start the stack with `docker compose up --build` and verify all agents can reach the Anthropic API end-to-end with a real `ANTHROPIC_API_KEY`.
