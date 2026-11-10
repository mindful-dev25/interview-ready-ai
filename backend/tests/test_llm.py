import asyncio
import json

import anthropic
import httpx2
import pytest

from app.core.llm import (
    LLMAuthenticationError,
    LLMClient,
    LLMConfigurationError,
    LLMGenerationError,
    LLMMalformedResponseError,
    LLMRateLimitError,
)
from app.core.llm_json import coerce_str_list, parse_json_response


def client_with(handler) -> LLMClient:
    """A client whose HTTP layer is the given handler, so nothing reaches the network."""
    return LLMClient(
        api_key="test-key",
        model="test-model",
        http_client=anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler)),
    )


def text(value: str) -> dict:
    return {"type": "text", "text": value}


def message(*blocks: dict, stop_reason: str = "end_turn", **extra) -> httpx2.Response:
    body = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "test-model",
        "content": list(blocks),
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 1},
        **extra,
    }
    return httpx2.Response(200, json=body)


def error(status: int, kind: str, detail: str) -> httpx2.Response:
    return httpx2.Response(
        status,
        headers={"retry-after-ms": "1"},
        json={"type": "error", "error": {"type": kind, "message": detail}},
    )


def test_generate_sends_prompt_and_system_prompt():
    requests = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return message(text("  hello  "))

    reply = asyncio.run(client_with(handler).generate(" hi ", system_prompt=" Be brief. "))

    assert reply == "hello"
    body = json.loads(requests[0].content)
    assert body["model"] == "test-model"
    assert body["system"] == "Be brief."
    assert body["messages"] == [{"role": "user", "content": "hi"}]
    assert body["fallbacks"] == "default"
    sent_key = requests[0].headers.get("x-api-key") or requests[0].headers.get("authorization", "")
    assert "test-key" in sent_key
    assert "server-side-fallback-2026-07-01" in requests[0].headers["anthropic-beta"]


def test_generate_returns_only_text_blocks():
    thinking = {"type": "thinking", "thinking": "", "signature": "sig"}
    client = client_with(lambda request: message(thinking, text("first "), text("second")))

    assert asyncio.run(client.generate("hi")) == "first second"


def test_generate_retries_after_rate_limit():
    calls = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        if len(calls) == 1:
            return error(429, "rate_limit_error", "slow down")
        return message(text("hello"))

    assert asyncio.run(client_with(handler).generate("hi")) == "hello"
    assert len(calls) == 2


def test_generate_gives_up_after_repeated_rate_limits():
    calls = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        return error(429, "rate_limit_error", "slow down")

    with pytest.raises(LLMRateLimitError, match="slow down"):
        asyncio.run(client_with(handler).generate("hi"))
    assert len(calls) == 3


def test_generate_reports_rejected_api_key_without_retrying():
    calls = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        return error(401, "authentication_error", "invalid x-api-key")

    with pytest.raises(LLMAuthenticationError, match="invalid x-api-key"):
        asyncio.run(client_with(handler).generate("hi"))
    assert len(calls) == 1


def test_generate_raises_when_claude_declines():
    refusal = message(
        stop_reason="refusal",
        stop_details={"type": "refusal", "category": "cyber", "explanation": None},
    )

    with pytest.raises(LLMGenerationError, match="category: cyber"):
        asyncio.run(client_with(lambda request: refusal).generate("hi"))


def test_generate_raises_when_reply_has_no_text():
    with pytest.raises(LLMMalformedResponseError):
        asyncio.run(client_with(lambda request: message()).generate("hi"))


def test_generate_requires_an_api_key():
    calls = []
    client = LLMClient(
        api_key="  ",
        model="test-model",
        http_client=anthropic.DefaultAsyncHttpxClient(
            transport=httpx2.MockTransport(lambda request: calls.append(request))
        ),
    )

    with pytest.raises(LLMConfigurationError, match="ANTHROPIC_API_KEY"):
        asyncio.run(client.generate("hi"))
    assert calls == []


def test_generate_reuses_one_sdk_client_across_calls():
    client = client_with(lambda request: message(text("ok")))

    async def run() -> bool:
        await client.generate("first")
        first = client._client
        await client.generate("second")
        same = client._client is first
        await client.aclose()
        return same

    assert asyncio.run(run())


def test_parse_json_response_strips_code_fence():
    assert parse_json_response('```json\n{"a": 1}\n```', expect=dict, context="testing") == {"a": 1}


def test_parse_json_response_finds_list_inside_wrapper_object():
    reply = '{"questions": [{"question": "Why us?"}]}'

    assert parse_json_response(reply, expect=list, context="testing") == [{"question": "Why us?"}]


def test_parse_json_response_rejects_non_json():
    with pytest.raises(LLMMalformedResponseError):
        parse_json_response("no json here", expect=dict, context="testing")


def test_coerce_str_list_wraps_scalars_and_drops_blanks():
    assert coerce_str_list("Python") == ["Python"]
    assert coerce_str_list(["Python", " ", 3]) == ["Python", "3"]
    assert coerce_str_list(None) == []
