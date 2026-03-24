# LLM Gateway Replacement Design

**Date:** 2026-03-24
**Status:** Approved
**Scope:** Replace LiteLLM with an in-house `backend/llm.py` abstraction layer

---

## Goal

Remove the LiteLLM dependency (pinned to 1.82.6 due to supply chain attack in 1.82.7–1.82.8) and replace it with a thin, in-house provider abstraction. The replacement must:

- Retain provider-agnostic routing via `provider/model` env vars (no code changes to swap providers)
- Support Anthropic at launch; be easily extensible to OpenAI and VertexAI
- Eliminate the third-party gateway dependency entirely

---

## Section 1: Interface & Data Model

A new `backend/llm.py` module is the single entry point for all LLM calls.

### Data model

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]

@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
```

### Public function

```python
def complete(
    model: str,                        # "anthropic/claude-haiku-4-5", "openai/gpt-4o-mini", etc.
    messages: list[dict],              # OpenAI-format messages
    max_tokens: int = 1024,
    tools: list[dict] | None = None,   # OpenAI-format tool definitions
) -> LLMResponse:
```

The **canonical internal message format is OpenAI-style** throughout the codebase:

```python
[
    {"role": "system",    "content": "..."},
    {"role": "user",      "content": "..."},
    {"role": "assistant", "content": "...", "tool_calls": [...]},
    {"role": "tool",      "tool_call_id": "...", "name": "...", "content": "..."},
]
```

Callers never import provider SDKs directly.

---

## Section 2: Provider Dispatch

`complete()` splits `model` on the first `/` to extract the provider prefix and dispatches to a private adapter function:

```python
def complete(model, messages, max_tokens=1024, tools=None) -> LLMResponse:
    provider, model_name = model.split("/", 1)
    match provider:
        case "anthropic": return _anthropic_complete(model_name, messages, max_tokens, tools)
        case "openai":    return _openai_complete(model_name, messages, max_tokens, tools)
        case _:           raise ValueError(f"Unsupported provider: {provider!r}")
```

Adding a new provider = one `_<provider>_complete()` function + one `case` line.

---

## Section 3: Anthropic Adapter

`_anthropic_complete()` handles three translations. Exceptions from the Anthropic SDK propagate unchanged so callers' existing `try/except` blocks continue to work.

### 3a. Messages → Anthropic format

The Anthropic SDK takes `system=` as a separate string parameter. All `role: "system"` entries are extracted and joined; the rest are passed as `messages=`.

**Tool result messages** (`role: "tool"`) map to Anthropic's format. Consecutive tool result entries must be **merged into a single `user` message** — sending two separate `user` messages will cause an Anthropic API validation error:
```python
# OpenAI (internal format) — two separate tool results
{"role": "tool", "tool_call_id": "tc_1", "name": "search_jobs", "content": "...result 1..."}
{"role": "tool", "tool_call_id": "tc_2", "name": "search_jobs", "content": "...result 2..."}

# Anthropic SDK — merged into one user message
{"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": "tc_1", "content": "...result 1..."},
    {"type": "tool_result", "tool_use_id": "tc_2", "content": "...result 2..."},
]}
```

**Assistant messages containing tool calls** (re-sent in the agentic loop) must be translated from OpenAI format to Anthropic's `tool_use` content block format. A `None` content value must be omitted. The `arguments` field may be a JSON string (if sourced from a raw OpenAI response) — it must be parsed with `json.loads()` before assigning to `input`:
```python
# OpenAI (internal format)
{"role": "assistant", "content": None, "tool_calls": [
    {"id": "tc_1", "type": "function", "function": {"name": "search_jobs", "arguments": "{...}"}}
]}

# Anthropic SDK
{"role": "assistant", "content": [
    {"type": "tool_use", "id": "tc_1", "name": "search_jobs", "input": {...}}  # dict, not string
]}
```

Note: after migration, `job_scout.py` appends `ToolCall.arguments` (already a `dict`) to the message history — so `json.loads()` is only needed in the adapter for any legacy string-format `arguments` values.

Without this translation, the agentic loop in `job_scout.py` will fail on the second Anthropic API call.

### 3b. Tools → Anthropic format

```python
# OpenAI (internal format)
{"type": "function", "function": {"name": "search_jobs", "description": "...", "parameters": {...}}}

# Anthropic SDK
{"name": "search_jobs", "description": "...", "input_schema": {...}}
```

### 3c. Response → LLMResponse

Iterate `response.content` blocks:
- `type: "text"` → `LLMResponse.content`
- `type: "tool_use"` → `ToolCall(id=block.id, name=block.name, arguments=block.input)`
- If no `text` block is present (pure tool-call response), `LLMResponse.content` is `None`

---

## Section 4: Call-site Changes

Six files change minimally.

### Simple completions (5 files)

`orchestrator.py`, `applicator.py`, `outreach.py`, `tools/hr_finder.py`, `tools/resume_tools.py`:

```python
# Before
import litellm
response = litellm.completion(model=..., messages=[...], max_tokens=...)
text = response.choices[0].message.content

# After
from backend import llm
response = llm.complete(model=..., messages=[...], max_tokens=...)
text = response.content
```

### Tool calling loop (`job_scout.py`)

Four changes:
1. `litellm.completion(...)` → `llm.complete(...)`
2. Check `if response.tool_calls:` instead of `finish_reason == "tool_calls"`
3. Iterate `response.tool_calls` as `ToolCall` objects — `tc.id`, `tc.name`, `tc.arguments` — instead of parsing JSON from `tc.function.arguments`
4. Remove `json.loads(tc.function.arguments)` — `ToolCall.arguments` is already a `dict`; wrapping it in `json.loads()` would double-decode

The `TOOLS` list in `job_scout.py` stays in OpenAI format; `llm.py` translates internally.

---

## Section 5: Dependencies

### Remove
- Run `uv remove litellm` inside the container (never edit `pyproject.toml` directly)

### Add
- Run `uv add anthropic` inside the container to add the latest clean release

### Future
- `openai` added via `uv add openai` when OpenAI provider support is needed
- `google-cloud-aiplatform` or `vertexai` added when VertexAI support is needed

---

## Section 6: Tests

All tests mock at the `llm.complete` boundary rather than provider-specific internals:

```python
# Before (nested MagicMock chain)
with patch("backend.agents.job_scout.litellm.completion") as mock:
    mock.return_value = MagicMock(choices=[MagicMock(finish_reason="tool_calls", message=...)])

# After (simple LLMResponse)
with patch("backend.agents.job_scout.llm.complete") as mock:
    mock.return_value = LLMResponse(
        content=None,
        tool_calls=[ToolCall(id="tc_1", name="search_jobs", arguments={...})]
    )
```

All existing tests are updated to use the new mock shape. A new `backend/tests/test_llm.py` is added to test the adapter translation logic in isolation — specifically: tool_use message translation, consecutive tool result merging, and `None` content handling. These paths are the highest-risk new code and are not exercised by the call-site tests.

---

## Files Changed

| File | Change |
|---|---|
| `backend/llm.py` | **New** — in-house gateway module |
| `backend/pyproject.toml` | Remove `litellm`, add `anthropic` |
| `backend/uv.lock` | Regenerate |
| `backend/agents/job_scout.py` | Swap import + update tool-call loop |
| `backend/agents/orchestrator.py` | Swap import + response access |
| `backend/agents/applicator.py` | Swap import + response access |
| `backend/agents/outreach.py` | Swap import + response access |
| `backend/tools/hr_finder.py` | Swap import + response access |
| `backend/tools/resume_tools.py` | Swap import + response access |
| `backend/tests/test_job_scout_agent.py` | Update mock shape + patch target |
| `backend/tests/test_orchestrator.py` | Update mock shape + patch target |
| `backend/tests/test_applicator_agent.py` | Update mock shape + patch target |
| `backend/tests/test_outreach_agent.py` | Update mock shape + patch target |
| `backend/tests/test_resume_tools.py` | Update mock shape + patch target |
| `backend/tests/test_hr_finder.py` | Update mock shape + patch target |
| `backend/tests/test_llm.py` | **New** — adapter translation unit tests |

---

## Provider Switching

No code changes needed to swap providers — update env vars only:

```bash
# Anthropic (default)
SCOUT_MODEL=anthropic/claude-haiku-4-5
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI (when _openai_complete is implemented)
SCOUT_MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=sk-...

# VertexAI (when _vertexai_complete is implemented)
SCOUT_MODEL=vertexai/gemini-1.5-flash
GOOGLE_APPLICATION_CREDENTIALS=...
```

Each agent can use a different provider independently.
