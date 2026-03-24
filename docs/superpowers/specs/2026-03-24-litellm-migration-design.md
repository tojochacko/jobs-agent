# LiteLLM Migration Design

**Date:** 2026-03-24
**Status:** Approved
**Scope:** Replace Anthropic SDK with LiteLLM across all agents for provider-agnostic LLM calls

---

## Goal

Swap the Anthropic SDK for LiteLLM so that the LLM provider (Anthropic, OpenAI, Gemini, Ollama, etc.) can be changed via environment variable without touching code.

## Approach

Direct `litellm.completion()` calls in each agent. No wrapper layer. Full migration of all 5 files including the agentic tool use loop in `job_scout.py`.

---

## Section 1: Dependencies & Config

### `requirements.txt`
- Remove: `anthropic>=0.40.0`
- Add: `litellm>=1.40.0`

LiteLLM installs provider SDKs lazily — no separate `anthropic` or `openai` package needed.

### `backend/config.py`
Model fields change from bare names to provider-prefixed strings:

| Field | Old default | New default |
|---|---|---|
| `ORCHESTRATOR_MODEL` | `claude-haiku-4-5` | `anthropic/claude-haiku-4-5` |
| `SCOUT_MODEL` | `claude-haiku-4-5` | `anthropic/claude-haiku-4-5` |
| `APPLICATOR_MODEL` | `claude-haiku-4-5` | `anthropic/claude-haiku-4-5` |
| `OUTREACH_MODEL` | `claude-haiku-4-5` | `anthropic/claude-haiku-4-5` |

API keys: keep `ANTHROPIC_API_KEY`. Add optional `OPENAI_API_KEY: str = ""` and `GEMINI_API_KEY: str = ""` as documentation anchors. LiteLLM reads all of these from env automatically — no explicit passing needed.

---

## Section 2: Simple Agents

Files: `orchestrator.py`, `applicator.py`, `outreach.py`, `tools/resume_tools.py`

### Pattern change

**Before (Anthropic SDK):**
```python
import anthropic
client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
response = client.messages.create(
    model=settings.SCOUT_MODEL,
    max_tokens=1024,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": "..."}],
)
for block in response.content:
    if getattr(block, "type", None) == "text":
        return block.text
```

**After (LiteLLM):**
```python
import litellm
response = litellm.completion(
    model=settings.SCOUT_MODEL,
    max_tokens=1024,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "..."},
    ],
)
return response.choices[0].message.content
```

Key differences:
- No client instantiation — `litellm.completion()` is module-level
- `system` becomes a `role: "system"` message prepended to the list
- Response: `response.choices[0].message.content` (OpenAI-compatible)
- No API key passed — LiteLLM reads from env

---

## Section 3: Job Scout Tool Use Loop

File: `agents/job_scout.py`

This file runs an agentic loop using tool calling. The loop logic is unchanged; only the message/response format changes.

### Tool definition

**Before (Anthropic format):**
```python
TOOLS = [{"name": "search_jobs", "description": "...", "input_schema": {...}}]
```

**After (OpenAI/LiteLLM format):**
```python
TOOLS = [{"type": "function", "function": {"name": "search_jobs", "description": "...", "parameters": {...}}}]
```

### Response format mapping

| Anthropic | LiteLLM / OpenAI |
|---|---|
| `response.stop_reason == "tool_use"` | `response.choices[0].finish_reason == "tool_calls"` |
| iterate `response.content` for `type == "tool_use"` | iterate `response.choices[0].message.tool_calls` |
| `block.id`, `block.name`, `block.input` | `tc.id`, `tc.function.name`, `json.loads(tc.function.arguments)` |
| `type == "text"` block for final output | `response.choices[0].message.content` |
| `tool_result` user message with `tool_use_id` | `role: "tool"` message with `tool_call_id` |

### Tool result message format

**Before:**
```python
{"type": "tool_result", "tool_use_id": block.id, "content": result}
```

**After:**
```python
{"role": "tool", "tool_call_id": tc.id, "content": result}
```

### Assistant message appended to history

**Before:**
```python
messages.append({"role": "assistant", "content": response.content})
```

**After:**
```python
messages.append(response.choices[0].message)
```

---

## Section 4: Error Handling & Tests

### Error handling
LiteLLM raises `litellm.exceptions.APIError` and subclasses. Existing broad `except Exception` handlers in `applicator.py` and `orchestrator.py` cover this. No changes to error handling logic.

### Tests
All tests currently mock `anthropic.Anthropic`. After migration, tests mock `litellm.completion` directly:

**Before:**
```python
with patch("backend.agents.job_scout.anthropic.Anthropic") as MockClient:
    client = MagicMock()
    MockClient.return_value = client
    client.messages.create.return_value = mock_response
```

**After:**
```python
with patch("backend.agents.job_scout.litellm.completion") as mock_completion:
    mock_completion.return_value = mock_response
```

Mock response objects change shape to OpenAI format. The `_tool_use_response` and `_end_turn_response` helpers in `test_job_scout_agent.py` are rewritten:

```python
def _tool_use_response(tool_id, tool_input):
    tc = MagicMock()
    tc.id = tool_id
    tc.function.name = "search_jobs"
    tc.function.arguments = json.dumps(tool_input)
    msg = MagicMock()
    msg.tool_calls = [tc]
    msg.content = None
    choice = MagicMock()
    choice.finish_reason = "tool_calls"
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp

def _end_turn_response(scored_jobs):
    msg = MagicMock()
    msg.content = json.dumps(scored_jobs)
    msg.tool_calls = None
    choice = MagicMock()
    choice.finish_reason = "stop"
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp
```

No new tests needed — existing coverage is sufficient once updated.

---

## Files Changed

| File | Change |
|---|---|
| `requirements.txt` | Remove `anthropic`, add `litellm` |
| `backend/config.py` | Prefix model defaults, add optional provider key fields |
| `backend/agents/job_scout.py` | Full loop rewrite to OpenAI tool calling format |
| `backend/agents/orchestrator.py` | Simple pattern swap |
| `backend/agents/applicator.py` | Simple pattern swap |
| `backend/agents/outreach.py` | Simple pattern swap |
| `backend/tools/resume_tools.py` | Simple pattern swap |
| `backend/tests/test_job_scout_agent.py` | Rewrite mock helpers + patch targets |
| `backend/tests/test_orchestrator.py` | Update patch target + response shape |
| `backend/tests/test_applicator_agent.py` | Update patch target + response shape |
| `backend/tests/test_outreach_agent.py` | Update patch target + response shape |
| `backend/tests/test_resume_tools.py` | Update patch target + response shape |

---

## Provider Switching

To switch provider, update model env vars:

```bash
# Use OpenAI
SCOUT_MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=sk-...

# Use Gemini
SCOUT_MODEL=gemini/gemini-1.5-flash
GEMINI_API_KEY=...

# Use local Ollama
SCOUT_MODEL=ollama/llama3
# No API key needed
```

Each agent can use a different provider independently.
