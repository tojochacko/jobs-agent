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


def test_complete_missing_slash_raises():
    with pytest.raises(ValueError, match="provider/model"):
        complete("claude-haiku-4-5", [{"role": "user", "content": "hi"}])


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


# --- openai tests ---

def _openai_text_resp(text: str):
    message = MagicMock()
    message.content = text
    message.tool_calls = None
    choice = MagicMock()
    choice.message = message
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _openai_tool_resp(tool_id: str, name: str, arguments: dict):
    tc = MagicMock()
    tc.id = tool_id
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments)
    message = MagicMock()
    message.content = None
    message.tool_calls = [tc]
    choice = MagicMock()
    choice.message = message
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_complete_openai_simple_text():
    with patch("backend.llm.openai.OpenAI") as MockClient:
        MockClient.return_value.chat.completions.create.return_value = _openai_text_resp("Hello from GPT!")
        result = complete(
            "openai/gpt-4o-mini",
            [{"role": "user", "content": "Hi"}],
        )
    assert result.content == "Hello from GPT!"
    assert result.tool_calls == []


def test_complete_openai_tool_use():
    with patch("backend.llm.openai.OpenAI") as MockClient:
        MockClient.return_value.chat.completions.create.return_value = _openai_tool_resp(
            "tc_1", "search_jobs", {"query": "Python Engineer"}
        )
        result = complete(
            "openai/gpt-4o-mini",
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


def test_complete_openai_system_message_stays_in_messages():
    """OpenAI accepts system messages inline in the messages list (unlike Anthropic)."""
    with patch("backend.llm.openai.OpenAI") as MockClient:
        MockClient.return_value.chat.completions.create.return_value = _openai_text_resp("ok")
        complete(
            "openai/gpt-4o-mini",
            [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello"},
            ],
        )
    call_kwargs = MockClient.return_value.chat.completions.create.call_args.kwargs
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "You are helpful."


def test_complete_anthropic_assistant_tool_calls_dict_format():
    """Assistant messages with internal dict-format tool_calls (no 'function' key) are translated correctly."""
    with patch("backend.llm.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _anthropic_text_resp("done")
        complete(
            "anthropic/claude-haiku-4-5",
            [
                {"role": "user", "content": "Go"},
                {"role": "assistant", "content": None, "tool_calls": [
                    {"id": "tc_1", "name": "search_jobs", "arguments": {"query": "Python"}},
                ]},
                {"role": "tool", "tool_call_id": "tc_1", "name": "search_jobs", "content": "[]"},
            ],
        )
    call_kwargs = MockClient.return_value.messages.create.call_args.kwargs
    asst_msg = call_kwargs["messages"][1]
    assert asst_msg["role"] == "assistant"
    assert asst_msg["content"][0]["type"] == "tool_use"
    assert asst_msg["content"][0]["id"] == "tc_1"
    assert asst_msg["content"][0]["input"] == {"query": "Python"}
