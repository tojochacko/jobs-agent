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

`_anthropic_complete()` handles three translations:

### 3a. Messages → Anthropic format

The Anthropic SDK takes `system=` as a separate string parameter. All `role: "system"` entries are extracted and joined; the rest are passed as `messages=`.

Tool result messages (`role: "tool"`) map to Anthropic's format:
```python
# OpenAI (internal format)
{"role": "tool", "tool_call_id": "tc_1", "name": "search_jobs", "content": "...result..."}

# Anthropic SDK
{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tc_1", "content": "...result..."}]}
```

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

Three changes:
1. `litellm.completion(...)` → `llm.complete(...)`
2. Check `if response.tool_calls:` instead of `finish_reason == "tool_calls"`
3. Iterate `response.tool_calls` as `ToolCall` objects — `tc.id`, `tc.name`, `tc.arguments` — instead of parsing JSON from `tc.function.arguments`

The `TOOLS` list in `job_scout.py` stays in OpenAI format; `llm.py` translates internally.

---

## Section 5: Dependencies

### Remove
- `litellm==1.82.6` from `backend/pyproject.toml`

### Add
- `anthropic` (latest clean release) via `uv add anthropic`

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

All existing tests are updated to use the new mock shape. No new tests needed — coverage is unchanged.

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
