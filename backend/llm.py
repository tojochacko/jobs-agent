# backend/llm.py
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import anthropic
import openai

logger = logging.getLogger(__name__)


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
    if "/" not in model:
        raise ValueError(f"Model must be 'provider/model', got: {model!r}")
    provider, model_name = model.split("/", 1)

    logger.debug("LLM REQUEST  model=%s\n%s", model, json.dumps(messages, indent=2))

    match provider:
        case "anthropic":
            result = _anthropic_complete(model_name, messages, max_tokens, tools)
        case "openai":
            result = _openai_complete(model_name, messages, max_tokens, tools)
        case _:
            raise ValueError(f"Unsupported provider: {provider!r}")

    logger.debug(
        "LLM RESPONSE model=%s  content=%r  tool_calls=%s",
        model,
        result.content,
        json.dumps([{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in result.tool_calls], indent=2),
    )
    return result


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


# ---------------------------------------------------------------------------
# OpenAI adapter
# ---------------------------------------------------------------------------

def _openai_complete(
    model_name: str,
    messages: list[dict],
    max_tokens: int,
    tools: list[dict] | None,
) -> LLMResponse:
    client = openai.OpenAI()

    kwargs: dict[str, Any] = {
        "model": model_name,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools

    response = client.chat.completions.create(**kwargs)
    message = response.choices[0].message

    content: str | None = message.content or None
    tool_calls: list[ToolCall] = []
    if message.tool_calls:
        for tc in message.tool_calls:
            tool_calls.append(ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=json.loads(tc.function.arguments),
            ))

    return LLMResponse(content=content, tool_calls=tool_calls)
