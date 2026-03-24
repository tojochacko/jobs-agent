# LLM Gateway Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `litellm==1.82.6` with an in-house `backend/llm.py` module that routes `provider/model` strings to provider SDKs, starting with Anthropic.

**Architecture:** A new `backend/llm.py` exposes a single `complete(model, messages, max_tokens, tools) -> LLMResponse` function. It parses the `provider/model` prefix, dispatches to a private `_anthropic_complete()` adapter, and returns a normalized `LLMResponse(content, tool_calls)` dataclass. Callers swap `litellm.completion(...)` for `llm.complete(...)` and access `.content` / `.tool_calls` instead of `response.choices[0].message.content`.

**Tech Stack:** Python 3.12, `anthropic` SDK (latest), pytest + pytest-mock, uv

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/llm.py` | **Create** | Data model + dispatch + Anthropic adapter |
| `backend/tests/test_llm.py` | **Create** | Unit tests for the adapter translation logic |
| `backend/pyproject.toml` | Modify (via uv) | Remove litellm, add anthropic |
| `backend/uv.lock` | Regenerate | Pinned dependencies |
| `backend/agents/orchestrator.py` | Modify | Swap litellm → llm |
| `backend/agents/applicator.py` | Modify | Swap litellm → llm |
| `backend/agents/outreach.py` | Modify | Swap litellm → llm |
| `backend/tools/hr_finder.py` | Modify | Swap litellm → llm |
| `backend/tools/resume_tools.py` | Modify | Swap litellm → llm |
| `backend/agents/job_scout.py` | Modify | Swap litellm → llm + rewrite tool loop |
| `backend/tests/test_orchestrator.py` | Modify | Update mock shape + patch target |
| `backend/tests/test_applicator_agent.py` | Modify | Update mock shape + patch target |
| `backend/tests/test_outreach_agent.py` | Modify | Update mock shape + patch target |
| `backend/tests/test_hr_finder.py` | Modify | Update mock shape + patch target |
| `backend/tests/test_resume_tools.py` | Modify | Update mock shape + patch target |
| `backend/tests/test_job_scout_agent.py` | Modify | Update mock shape + patch target |

---

## Task 1: Create `backend/llm.py` — data model, dispatch, Anthropic adapter

**Files:**
- Create: `backend/llm.py`
- Create: `backend/tests/test_llm.py`

- [ ] **Step 1: Write `test_llm.py` with failing tests**

```python
# backend/tests/test_llm.py
import json
import pytest
from unittest.mock import patch, MagicMock
from backend.llm import complete, LLMResponse, ToolCall


# --- helpers ---

def _anthropic_text_resp(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    return resp


def _anthropic_tool_resp(tool_id: str, name: str, tool_input: dict):
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = tool_input
    resp = MagicMock()
    resp.content = [block]
    return resp


# --- tests ---

def test_complete_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unsupported provider"):
        complete("badprovider/some-model", [{"role": "user", "content": "hi"}])


def test_complete_anthropic_simple_text():
    with patch("backend.llm.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _anthropic_text_resp("Hello!")
        result = complete(
            "anthropic/claude-haiku-4-5",
            [{"role": "user", "content": "Hi"}],
        )
    assert result.content == "Hello!"
    assert result.tool_calls == []


def test_complete_anthropic_tool_use():
    with patch("backend.llm.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _anthropic_tool_resp(
            "tc_1", "search_jobs", {"query": "Python Engineer"}
        )
        result = complete(
            "anthropic/claude-haiku-4-5",
            [{"role": "user", "content": "Find jobs"}],
            tools=[{"type": "function", "function": {
                "name": "search_jobs",
                "description": "Search jobs",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            }}],
        )
    assert result.content is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "tc_1"
    assert result.tool_calls[0].name == "search_jobs"
    assert result.tool_calls[0].arguments == {"query": "Python Engineer"}


def test_complete_anthropic_system_message_extracted():
    """System messages are extracted and passed as `system=` param, not in messages."""
    with patch("backend.llm.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _anthropic_text_resp("ok")
        complete(
            "anthropic/claude-haiku-4-5",
            [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello"},
            ],
        )
    call_kwargs = MockClient.return_value.messages.create.call_args.kwargs
    assert call_kwargs["system"] == "You are helpful."
    # system message must not appear in messages list
    assert all(m["role"] != "system" for m in call_kwargs["messages"])


def test_complete_anthropic_tool_results_merged():
    """Consecutive role:tool messages are merged into a single Anthropic user message."""
    with patch("backend.llm.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _anthropic_text_resp("done")
        complete(
            "anthropic/claude-haiku-4-5",
            [
                {"role": "user", "content": "Find jobs"},
                {"role": "assistant", "content": None, "tool_calls": [
                    {"id": "tc_1", "type": "function", "function": {"name": "search_jobs", "arguments": json.dumps({"query": "Python"})}},
                    {"id": "tc_2", "type": "function", "function": {"name": "search_jobs", "arguments": json.dumps({"query": "Django"})}},
                ]},
                {"role": "tool", "tool_call_id": "tc_1", "name": "search_jobs", "content": "[]"},
                {"role": "tool", "tool_call_id": "tc_2", "name": "search_jobs", "content": "[]"},
            ],
        )
    call_kwargs = MockClient.return_value.messages.create.call_args.kwargs
    anthropic_messages = call_kwargs["messages"]
    # The two tool results must be the last message as a single user message with list content
    last = anthropic_messages[-1]
    assert last["role"] == "user"
    assert isinstance(last["content"], list)
    assert len(last["content"]) == 2
    assert last["content"][0]["type"] == "tool_result"
    assert last["content"][1]["type"] == "tool_result"


def test_complete_anthropic_assistant_tool_calls_translated():
    """Assistant messages with OpenAI-format tool_calls are translated to Anthropic tool_use blocks."""
    with patch("backend.llm.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _anthropic_text_resp("done")
        complete(
            "anthropic/claude-haiku-4-5",
            [
                {"role": "user", "content": "Go"},
                {"role": "assistant", "content": None, "tool_calls": [
                    {"id": "tc_1", "type": "function", "function": {
                        "name": "search_jobs",
                        "arguments": json.dumps({"query": "Python"}),
                    }},
                ]},
                {"role": "tool", "tool_call_id": "tc_1", "name": "search_jobs", "content": "[]"},
            ],
        )
    call_kwargs = MockClient.return_value.messages.create.call_args.kwargs
    anthropic_messages = call_kwargs["messages"]
    # Second message should be assistant with tool_use content block
    asst_msg = anthropic_messages[1]
    assert asst_msg["role"] == "assistant"
    assert isinstance(asst_msg["content"], list)
    assert asst_msg["content"][0]["type"] == "tool_use"
    assert asst_msg["content"][0]["id"] == "tc_1"
    assert asst_msg["content"][0]["input"] == {"query": "Python"}  # dict, not string
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/test_llm.py -v"
```

Expected: `ModuleNotFoundError: No module named 'backend.llm'`

- [ ] **Step 3: Update dependencies**

```bash
docker compose run --rm backend sh -c "uv remove litellm && uv add anthropic"
```

Expected: `pyproject.toml` updated, `uv.lock` regenerated.

- [ ] **Step 4: Create `backend/llm.py`**

```python
# backend/llm.py
import json
from dataclasses import dataclass, field
from typing import Any

import anthropic


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


def complete(
    model: str,
    messages: list[dict],
    max_tokens: int = 1024,
    tools: list[dict] | None = None,
) -> LLMResponse:
    """Route an LLM call to the correct provider based on the 'provider/model' prefix."""
    provider, model_name = model.split("/", 1)
    match provider:
        case "anthropic":
            return _anthropic_complete(model_name, messages, max_tokens, tools)
        case _:
            raise ValueError(f"Unsupported provider: {provider!r}")


# ---------------------------------------------------------------------------
# Anthropic adapter
# ---------------------------------------------------------------------------

def _convert_messages_to_anthropic(messages: list[dict]) -> tuple[str, list[dict]]:
    """Extract system messages and convert remaining messages to Anthropic format."""
    system_parts: list[str] = []
    anthropic_messages: list[dict] = []

    i = 0
    while i < len(messages):
        msg = messages[i]
        role = msg["role"]

        if role == "system":
            system_parts.append(msg["content"])
            i += 1

        elif role == "tool":
            # Merge consecutive tool results into a single Anthropic user message
            tool_results = []
            while i < len(messages) and messages[i]["role"] == "tool":
                m = messages[i]
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": m["tool_call_id"],
                    "content": m["content"],
                })
                i += 1
            anthropic_messages.append({"role": "user", "content": tool_results})

        elif role == "assistant":
            tool_calls = msg.get("tool_calls") or []
            if tool_calls:
                content_blocks = []
                if msg.get("content"):
                    content_blocks.append({"type": "text", "text": msg["content"]})
                for tc in tool_calls:
                    if "function" in tc:
                        # OpenAI format: {"id": ..., "function": {"name": ..., "arguments": "..."}}
                        name = tc["function"]["name"]
                        raw_args = tc["function"]["arguments"]
                        args = raw_args if isinstance(raw_args, dict) else json.loads(raw_args)
                    else:
                        # ToolCall dict format: {"id": ..., "name": ..., "arguments": {...}}
                        name = tc["name"]
                        args = tc["arguments"]
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": name,
                        "input": args,
                    })
                anthropic_messages.append({"role": "assistant", "content": content_blocks})
            else:
                anthropic_messages.append({"role": "assistant", "content": msg.get("content", "")})
            i += 1

        else:
            anthropic_messages.append({"role": role, "content": msg["content"]})
            i += 1

    return "\n".join(system_parts), anthropic_messages


def _convert_tools_to_anthropic(tools: list[dict]) -> list[dict]:
    """Convert OpenAI-format tool definitions to Anthropic format."""
    result = []
    for tool in tools:
        fn = tool["function"]
        result.append({
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {}),
        })
    return result


def _anthropic_complete(
    model_name: str,
    messages: list[dict],
    max_tokens: int,
    tools: list[dict] | None,
) -> LLMResponse:
    client = anthropic.Anthropic()
    system, anthropic_messages = _convert_messages_to_anthropic(messages)

    kwargs: dict[str, Any] = {
        "model": model_name,
        "max_tokens": max_tokens,
        "messages": anthropic_messages,
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = _convert_tools_to_anthropic(tools)

    response = client.messages.create(**kwargs)

    content: str | None = None
    tool_calls: list[ToolCall] = []
    for block in response.content:
        if block.type == "text":
            content = block.text
        elif block.type == "tool_use":
            tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))

    return LLMResponse(content=content, tool_calls=tool_calls)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/test_llm.py -v"
```

Expected: 6 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/llm.py backend/tests/test_llm.py backend/pyproject.toml backend/uv.lock
git commit -m "feat: add in-house llm.py gateway, remove litellm"
```

---

## Task 2: Migrate `orchestrator.py` + update `test_orchestrator.py`

**Files:**
- Modify: `backend/agents/orchestrator.py:3,34,42`
- Modify: `backend/tests/test_orchestrator.py`

- [ ] **Step 1: Update `test_orchestrator.py` first (tests will fail)**

Replace the entire file:

```python
# backend/tests/test_orchestrator.py
from unittest.mock import patch
from backend.llm import LLMResponse, ToolCall

PREFERENCES = {
    "job_titles": ["Python Engineer"],
    "location": "Remote",
    "remote_hybrid": "remote",
    "experience_level": "senior",
    "domain": "backend",
    "company_size": ["startup"],
}

HIGH_MATCH_JOB = {
    "title": "Senior Python Engineer",
    "company": "Startup Co",
    "location": "Remote",
    "description": "FastAPI, PostgreSQL, Docker, fully remote senior backend role",
    "url": "https://startup.com/jobs/1",
}

LOW_MATCH_JOB = {
    "title": "Junior Marketing Analyst",
    "company": "Big Corp",
    "location": "New York",
    "description": "Excel, PowerPoint, marketing campaigns",
    "url": "https://bigcorp.com/jobs/2",
}


def test_score_job_returns_float():
    with patch("backend.agents.orchestrator.llm.complete") as mock_complete:
        mock_complete.return_value = LLMResponse(content="0.92")
        from backend.agents.orchestrator import score_job
        score = score_job(HIGH_MATCH_JOB, PREFERENCES)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
    assert score == 0.92


def test_score_job_handles_malformed_response():
    with patch("backend.agents.orchestrator.llm.complete") as mock_complete:
        mock_complete.return_value = LLMResponse(content="I cannot score this job.")
        from backend.agents.orchestrator import score_job
        score = score_job(LOW_MATCH_JOB, PREFERENCES)
    assert score == 0.0


def test_score_job_clamps_to_valid_range():
    with patch("backend.agents.orchestrator.llm.complete") as mock_complete:
        mock_complete.return_value = LLMResponse(content="1.5")
        from backend.agents.orchestrator import score_job
        score = score_job(HIGH_MATCH_JOB, PREFERENCES)
    assert score == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/test_orchestrator.py -v"
```

Expected: `AttributeError: module 'backend.agents.orchestrator' has no attribute 'llm'`

- [ ] **Step 3: Update `backend/agents/orchestrator.py`**

Replace lines 3 and 34 and 42:

```python
# line 3: replace
import litellm
# with:
from backend import llm

# line 34: replace
        response = litellm.completion(
            model=settings.ORCHESTRATOR_MODEL,
            max_tokens=16,
            messages=[
                {"role": "system", "content": SCORE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
# with:
        response = llm.complete(
            model=settings.ORCHESTRATOR_MODEL,
            max_tokens=16,
            messages=[
                {"role": "system", "content": SCORE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )

# line 42: replace
        raw = response.choices[0].message.content.strip()
# with:
        raw = response.content.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/test_orchestrator.py -v"
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/orchestrator.py backend/tests/test_orchestrator.py
git commit -m "refactor: migrate orchestrator to in-house llm module"
```

---

## Task 3: Migrate `applicator.py` + update `test_applicator_agent.py`

**Files:**
- Modify: `backend/agents/applicator.py:3,41-55,62,64`
- Modify: `backend/tests/test_applicator_agent.py`

- [ ] **Step 1: Update `test_applicator_agent.py` first**

```python
# backend/tests/test_applicator_agent.py
import json
import pytest
from unittest.mock import patch
from backend.llm import LLMResponse, ToolCall

MOCK_FORM = {
    "fields": [
        {"name": "first_name", "type": "text", "id": "first_name", "placeholder": ""},
        {"name": "email", "type": "email", "id": "email", "placeholder": ""},
    ],
    "url": "https://acme.com/apply",
    "title": "Apply at Acme",
}

MOCK_TAILORED = "John Doe\nSenior Python Engineer\nTailored for Acme role"


def test_run_applicator_returns_result():
    payload = json.dumps({"first_name": "John", "email": "john@example.com"})
    with patch("backend.agents.applicator.llm.complete") as mock_complete, \
         patch("backend.agents.applicator.fetch_application_form", return_value=MOCK_FORM), \
         patch("backend.agents.applicator.tailor_resume", return_value=MOCK_TAILORED):
        mock_complete.return_value = LLMResponse(content=payload)
        from backend.agents.applicator import run_applicator
        result = run_applicator(
            job_id=1,
            job_url="https://acme.com/apply",
            job_description="Senior Python Engineer",
            resume_path="uploads/resume.txt",
        )
    assert result["status"] == "ready"
    assert "form_payload" in result
    assert "tailored_resume" in result


def test_run_applicator_returns_manual_required_on_form_failure():
    with patch("backend.agents.applicator.fetch_application_form",
               return_value={"status": "manual_required", "url": "https://acme.com/apply"}), \
         patch("backend.agents.applicator.tailor_resume", return_value=MOCK_TAILORED):
        from backend.agents.applicator import run_applicator
        result = run_applicator(1, "https://acme.com/apply", "JD", "uploads/resume.txt")
    assert result["status"] == "manual_required"


def test_run_applicator_handles_invalid_json_from_llm():
    with patch("backend.agents.applicator.llm.complete") as mock_complete, \
         patch("backend.agents.applicator.fetch_application_form", return_value=MOCK_FORM), \
         patch("backend.agents.applicator.tailor_resume", return_value=MOCK_TAILORED):
        mock_complete.return_value = LLMResponse(content="not valid json at all")
        from backend.agents.applicator import run_applicator
        result = run_applicator(1, "https://acme.com/apply", "JD", "uploads/resume.txt")
    assert result["status"] == "ready"
    assert result["form_payload"] == {}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/test_applicator_agent.py -v"
```

Expected: `AttributeError: module 'backend.agents.applicator' has no attribute 'llm'`

- [ ] **Step 3: Update `backend/agents/applicator.py`**

```python
# line 3: replace
import litellm
# with:
from backend import llm

# lines 41–55: replace the litellm.completion call block
        response = litellm.completion(
            model=settings.APPLICATOR_MODEL,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Form fields:\n{json.dumps(form_result.get('fields', []), indent=2)}\n\n"
                        f"Tailored Resume:\n{tailored}\n\n"
                        "Return a JSON object mapping each field name to its value."
                    ),
                },
            ],
        )
# with:
        response = llm.complete(
            model=settings.APPLICATOR_MODEL,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Form fields:\n{json.dumps(form_result.get('fields', []), indent=2)}\n\n"
                        f"Tailored Resume:\n{tailored}\n\n"
                        "Return a JSON object mapping each field name to its value."
                    ),
                },
            ],
        )

# line 62: replace
        payload = json.loads(response.choices[0].message.content)
# with:
        payload = json.loads(response.content)

# line 64: replace
        logger.warning(f"LLM returned non-JSON payload for job {job_id}: {response.choices[0].message.content[:100]}")
# with:
        logger.warning(f"LLM returned non-JSON payload for job {job_id}: {(response.content or '')[:100]}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/test_applicator_agent.py -v"
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/applicator.py backend/tests/test_applicator_agent.py
git commit -m "refactor: migrate applicator to in-house llm module"
```

---

## Task 4: Migrate `outreach.py` + update `test_outreach_agent.py`

**Files:**
- Modify: `backend/agents/outreach.py:2,22-38,39`
- Modify: `backend/tests/test_outreach_agent.py`

- [ ] **Step 1: Update `test_outreach_agent.py` first**

```python
# backend/tests/test_outreach_agent.py
import pytest
from unittest.mock import patch
from backend.llm import LLMResponse, ToolCall

MOCK_HR = {"hr_name": "Jane Smith", "hr_email": "jane@acme.com", "hr_confidence": "search_result"}
MOCK_COVER = "Dear Jane,\n\nI am excited to apply for the Python Engineer role at Acme..."
MOCK_RESUME_PATH = "uploads/tailored_1.pdf"


def test_run_outreach_returns_draft():
    with patch("backend.agents.outreach.find_hr_contact", return_value=MOCK_HR), \
         patch("backend.agents.outreach.generate_cover_letter", return_value=MOCK_COVER), \
         patch("backend.agents.outreach.tailor_resume", return_value=MOCK_RESUME_PATH):
        from backend.agents.outreach import run_outreach
        result = run_outreach(
            job_id=1,
            company="Acme",
            job_description="Python Engineer at Acme",
            resume_path="uploads/master.pdf",
            output_dir="uploads",
        )
    assert result["hr_email"] == "jane@acme.com"
    assert result["cover_letter"] == MOCK_COVER
    assert result["resume_version_path"] == MOCK_RESUME_PATH
    assert result["hr_confidence"] == "search_result"


def test_run_outreach_proceeds_with_unknown_contact():
    unknown_hr = {"hr_name": "", "hr_email": "", "hr_confidence": "unknown"}
    with patch("backend.agents.outreach.find_hr_contact", return_value=unknown_hr), \
         patch("backend.agents.outreach.generate_cover_letter", return_value="Cover letter"), \
         patch("backend.agents.outreach.tailor_resume", return_value="uploads/t.pdf"):
        from backend.agents.outreach import run_outreach
        result = run_outreach(1, "Acme", "JD", "uploads/master.pdf", "uploads")
    assert result["hr_confidence"] == "unknown"
    assert result["cover_letter"] == "Cover letter"


def test_generate_cover_letter_returns_string():
    cover = "Dear Jane,\n\nI am excited to apply for the Python Engineer role at Acme."
    with patch("backend.agents.outreach.llm.complete") as mock_complete, \
         patch("backend.tools.resume_tools._read_resume", return_value="Resume content"):
        mock_complete.return_value = LLMResponse(content=cover)
        from backend.agents.outreach import generate_cover_letter
        result = generate_cover_letter(
            job_description="Python Engineer at Acme",
            resume_path="uploads/resume.txt",
            company="Acme",
            hr_name="Jane Smith",
        )
    assert isinstance(result, str)
    assert "Jane" in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/test_outreach_agent.py -v"
```

Expected: `AttributeError: module 'backend.agents.outreach' has no attribute 'llm'`

- [ ] **Step 3: Update `backend/agents/outreach.py`**

```python
# line 2: replace
import litellm
# with:
from backend import llm

# lines 22–38: replace the litellm.completion call
    response = litellm.completion(
        model=settings.OUTREACH_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": COVER_LETTER_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Company: {company}\n\n"
                    f"Job Description:\n{job_description}\n\n"
                    f"Resume:\n{resume_content}\n\n"
                    f"Salutation: {greeting}\n\n"
                    "Write the cover letter."
                ),
            },
        ],
    )
# with:
    response = llm.complete(
        model=settings.OUTREACH_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": COVER_LETTER_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Company: {company}\n\n"
                    f"Job Description:\n{job_description}\n\n"
                    f"Resume:\n{resume_content}\n\n"
                    f"Salutation: {greeting}\n\n"
                    "Write the cover letter."
                ),
            },
        ],
    )

# line 39: replace
    return response.choices[0].message.content or ""
# with:
    return response.content or ""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/test_outreach_agent.py -v"
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/outreach.py backend/tests/test_outreach_agent.py
git commit -m "refactor: migrate outreach to in-house llm module"
```

---

## Task 5: Migrate `hr_finder.py` + update `test_hr_finder.py`

**Files:**
- Modify: `backend/tools/hr_finder.py:3,39-46,51`
- Modify: `backend/tests/test_hr_finder.py`

- [ ] **Step 1: Update `test_hr_finder.py` first**

```python
# backend/tests/test_hr_finder.py
import json
import pytest
from unittest.mock import patch
from backend.llm import LLMResponse, ToolCall

MOCK_SEARCH_RESULTS = [
    {
        "title": "Jane Smith - Recruiter at Acme Corp | LinkedIn",
        "link": "https://linkedin.com/in/jane-smith",
        "snippet": "Jane Smith is a Technical Recruiter at Acme Corp. Email: j.smith@acme.com"
    }
]


def test_find_hr_contact_returns_dict():
    contact_json = '{"hr_name": "Jane Smith", "hr_email": "j.smith@acme.com", "hr_confidence": "search_result"}'
    with patch("backend.tools.hr_finder.search_people", return_value=MOCK_SEARCH_RESULTS), \
         patch("backend.tools.hr_finder.llm.complete") as mock_complete:
        mock_complete.return_value = LLMResponse(content=contact_json)
        from backend.tools.hr_finder import find_hr_contact
        result = find_hr_contact(company="Acme Corp", job_title="Python Engineer")
    assert isinstance(result, dict)
    assert "hr_name" in result
    assert "hr_email" in result
    assert "hr_confidence" in result


def test_find_hr_contact_returns_unknown_when_no_results():
    with patch("backend.tools.hr_finder.search_people", return_value=[]):
        from backend.tools.hr_finder import find_hr_contact
        result = find_hr_contact(company="Unknown Co", job_title="Engineer")
    assert result["hr_confidence"] == "unknown"
    assert result["hr_email"] == ""


def test_find_hr_contact_handles_search_failure():
    with patch("backend.tools.hr_finder.search_people", side_effect=Exception("API error")):
        from backend.tools.hr_finder import find_hr_contact
        result = find_hr_contact(company="Acme", job_title="Engineer")
    assert result["hr_confidence"] == "unknown"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/test_hr_finder.py -v"
```

Expected: `AttributeError: module 'backend.tools.hr_finder' has no attribute 'llm'`

- [ ] **Step 3: Update `backend/tools/hr_finder.py`**

```python
# line 3: replace
import litellm
# with:
from backend import llm

# lines 39–46: replace the litellm.completion call
    try:
        response = litellm.completion(
            model=settings.OUTREACH_MODEL,
            max_tokens=256,
            messages=[
                {"role": "system", "content": EXTRACT_SYSTEM},
                {"role": "user", "content": f"Company: {company}\nJob: {job_title}\n\nSearch results:\n{snippets}"},
            ],
        )
    except Exception as e:
        logger.warning(f"LLM extraction failed: {e}")
        return {"hr_name": "", "hr_email": "", "hr_confidence": "unknown"}
# with:
    try:
        response = llm.complete(
            model=settings.OUTREACH_MODEL,
            max_tokens=256,
            messages=[
                {"role": "system", "content": EXTRACT_SYSTEM},
                {"role": "user", "content": f"Company: {company}\nJob: {job_title}\n\nSearch results:\n{snippets}"},
            ],
        )
    except Exception as e:
        logger.warning(f"LLM extraction failed: {e}")
        return {"hr_name": "", "hr_email": "", "hr_confidence": "unknown"}

# line 51: replace
    content = response.choices[0].message.content
# with:
    content = response.content
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/test_hr_finder.py -v"
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/tools/hr_finder.py backend/tests/test_hr_finder.py
git commit -m "refactor: migrate hr_finder to in-house llm module"
```

---

## Task 6: Migrate `resume_tools.py` + update `test_resume_tools.py`

**Files:**
- Modify: `backend/tools/resume_tools.py:1,60-70,71`
- Modify: `backend/tests/test_resume_tools.py`

- [ ] **Step 1: Update `test_resume_tools.py` first**

```python
# backend/tests/test_resume_tools.py
import os
import pytest
from pathlib import Path
from unittest.mock import patch
from backend.llm import LLMResponse, ToolCall


@pytest.fixture
def sample_resume(tmp_path):
    f = tmp_path / "resume.txt"
    f.write_text("John Doe\nSenior Python Engineer\nExperience: FastAPI, PostgreSQL, Docker")
    return str(f)


def test_tailor_resume_text_returns_string(sample_resume):
    with patch("backend.tools.resume_tools.llm.complete") as mock_complete:
        mock_complete.return_value = LLMResponse(content="Tailored resume text for Python role")
        from backend.tools.resume_tools import tailor_resume
        result = tailor_resume(
            job_description="Senior Python Engineer at Acme",
            master_resume_path=sample_resume,
            output_format="text",
            output_path="",
        )
    assert isinstance(result, str)
    assert "Tailored" in result


def test_tailor_resume_pdf_writes_file(sample_resume, tmp_path):
    output_path = str(tmp_path / "tailored.pdf")
    with patch("backend.tools.resume_tools.llm.complete") as mock_complete, \
         patch("backend.tools.resume_tools._write_pdf") as mock_pdf:
        mock_complete.return_value = LLMResponse(content="Tailored resume content")
        from backend.tools.resume_tools import tailor_resume
        result = tailor_resume(
            job_description="Senior Python Engineer at Acme",
            master_resume_path=sample_resume,
            output_format="pdf",
            output_path=output_path,
        )
    assert result == output_path
    mock_pdf.assert_called_once_with("Tailored resume content", output_path)


def test_tailor_resume_reads_resume_content(sample_resume):
    from backend.tools.resume_tools import _read_resume
    content = _read_resume(sample_resume)
    assert "Senior Python Engineer" in content
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/test_resume_tools.py -v"
```

Expected: `AttributeError: module 'backend.tools.resume_tools' has no attribute 'llm'`

- [ ] **Step 3: Update `backend/tools/resume_tools.py`**

```python
# line 1: replace
import litellm
# with:
from backend import llm

# lines 60–70: replace the litellm.completion call
    response = litellm.completion(
        model=model or settings.APPLICATOR_MODEL,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": TAILOR_SYSTEM},
            {
                "role": "user",
                "content": f"Job Description:\n{job_description}\n\nMaster Resume:\n{resume_content}\n\nTailor the resume for this role.",
            },
        ],
    )
# with:
    response = llm.complete(
        model=model or settings.APPLICATOR_MODEL,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": TAILOR_SYSTEM},
            {
                "role": "user",
                "content": f"Job Description:\n{job_description}\n\nMaster Resume:\n{resume_content}\n\nTailor the resume for this role.",
            },
        ],
    )

# line 71: replace
    tailored_text = response.choices[0].message.content
# with:
    tailored_text = response.content
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/test_resume_tools.py -v"
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/tools/resume_tools.py backend/tests/test_resume_tools.py
git commit -m "refactor: migrate resume_tools to in-house llm module"
```

---

## Task 7: Migrate `job_scout.py` + update `test_job_scout_agent.py`

**Files:**
- Modify: `backend/agents/job_scout.py:2,68-109`
- Modify: `backend/tests/test_job_scout_agent.py`

- [ ] **Step 1: Update `test_job_scout_agent.py` first**

```python
# backend/tests/test_job_scout_agent.py
import json
import pytest
from unittest.mock import patch
from backend.llm import LLMResponse, ToolCall

PREFERENCES = {
    "job_titles": ["Python Engineer"],
    "location": "Remote",
    "remote_hybrid": "remote",
    "experience_level": "senior",
    "domain": "backend",
    "company_size": ["startup"],
}

MOCK_SERP_RESULTS = [
    {
        "title": "Senior Python Engineer",
        "company": "Acme",
        "location": "Remote",
        "description": "Build APIs",
        "url": "https://acme.com/jobs/1",
    }
]


def _tool_use_response(tool_id, tool_input):
    return LLMResponse(
        content=None,
        tool_calls=[ToolCall(id=tool_id, name="search_jobs", arguments=tool_input)],
    )


def _end_turn_response(scored_jobs):
    return LLMResponse(content=json.dumps(scored_jobs), tool_calls=[])


def test_run_job_scout_returns_scored_jobs():
    scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.9}]
    with patch("backend.agents.job_scout.llm.complete") as mock_complete, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS):
        mock_complete.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer", "location": "Remote"}),
            _end_turn_response(scored),
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert len(result) == 1
    assert result[0]["match_score"] == 0.9


def test_run_job_scout_filters_below_threshold():
    low_scored = [{**MOCK_SERP_RESULTS[0], "match_score": 0.3}]
    with patch("backend.agents.job_scout.llm.complete") as mock_complete, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS), \
         patch("backend.agents.job_scout.settings") as mock_settings:
        mock_settings.SCOUT_MODEL = "anthropic/claude-haiku-4-5"
        mock_settings.JOB_MATCH_THRESHOLD = 0.6
        mock_complete.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer", "location": "Remote"}),
            _end_turn_response(low_scored),
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert result == []


def test_run_job_scout_handles_malformed_response():
    """Agent returns non-JSON text — should return empty list gracefully."""
    with patch("backend.agents.job_scout.llm.complete") as mock_complete, \
         patch("backend.agents.job_scout.search_jobs", return_value=MOCK_SERP_RESULTS):
        mock_complete.side_effect = [
            _tool_use_response("tu_1", {"query": "Python Engineer"}),
            LLMResponse(content="Sorry, I could not find any jobs.", tool_calls=[]),
        ]
        from backend.agents.job_scout import run_job_scout
        result = run_job_scout(PREFERENCES)
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/test_job_scout_agent.py -v"
```

Expected: `AttributeError: module 'backend.agents.job_scout' has no attribute 'llm'`

- [ ] **Step 3: Update `backend/agents/job_scout.py`**

Replace line 2 and the `run_job_scout` function body:

```python
# line 2: replace
import litellm
# with:
from backend import llm
```

Replace the entire `run_job_scout` function (lines 57–109):

```python
def run_job_scout(preferences: dict) -> list[dict]:
    """Run the JobScout agentic loop. Returns jobs scoring >= JOB_MATCH_THRESHOLD."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Find and score jobs for these preferences:\n{json.dumps(preferences, indent=2)}\n\nSearch each job title. Return a JSON array of scored jobs.",
        },
    ]

    while True:
        response = llm.complete(
            model=settings.SCOUT_MODEL,
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
        )

        if response.tool_calls:
            messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.arguments},
                    }
                    for tc in response.tool_calls
                ],
            })
            for tc in response.tool_calls:
                result = _execute_tool(tc.name, tc.arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.name,
                    "content": result,
                })
            continue

        # end_turn / stop — parse final JSON output
        content = response.content
        if content:
            try:
                jobs = json.loads(content)
                return [j for j in jobs if j.get("match_score", 0) >= settings.JOB_MATCH_THRESHOLD]
            except (json.JSONDecodeError, TypeError):
                return []
        return []
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/test_job_scout_agent.py -v"
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/job_scout.py backend/tests/test_job_scout_agent.py
git commit -m "refactor: migrate job_scout to in-house llm module"
```

---

## Task 8: Run full test suite + verify no litellm references remain

**Files:** No changes — verification only.

- [ ] **Step 1: Run the full test suite**

```bash
docker compose run --rm backend sh -c "uv sync && pytest backend/tests/ -v"
```

Expected: All tests PASSED. Note any failures and fix before proceeding.

- [ ] **Step 2: Verify no litellm imports remain in source**

```bash
docker compose run --rm backend sh -c "grep -r 'litellm' backend/ --include='*.py'"
```

Expected: No output (zero matches). If any remain, fix them before proceeding.

---

## Quick Reference: Response Access Pattern

| Before (litellm) | After (llm) |
|---|---|
| `response.choices[0].message.content` | `response.content` |
| `response.choices[0].finish_reason == "tool_calls"` | `if response.tool_calls:` |
| `tc.function.name` | `tc.name` |
| `json.loads(tc.function.arguments)` | `tc.arguments` (already a dict) |
| `patch("...litellm.completion")` | `patch("...llm.complete")` |
| `MagicMock(choices=[MagicMock(...)])` | `LLMResponse(content=..., tool_calls=[...])` |
