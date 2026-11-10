import asyncio

import httpx
import pytest

from app.core.llm import GroqLLMClient, LLMMalformedResponseError, LLMRateLimitError
from app.core.llm_json import coerce_str_list, parse_json_response


def client_with(handler) -> GroqLLMClient:
    return GroqLLMClient(
        api_key="test-key",
        base_url="https://llm.test/v1",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )


def completion(text: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


def test_generate_retries_after_rate_limit():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"retry-after": "0"}, json={"error": {"message": "slow down"}})
        return completion("hello")

    assert asyncio.run(client_with(handler).generate("hi")) == "hello"
    assert len(calls) == 2


def test_generate_gives_up_after_repeated_rate_limits():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(429, headers={"retry-after": "0"}, json={"error": {"message": "slow down"}})

    with pytest.raises(LLMRateLimitError, match="slow down"):
        asyncio.run(client_with(handler).generate("hi"))
    assert len(calls) == 3


def test_generate_reuses_one_http_client_across_calls():
    client = client_with(lambda request: completion("ok"))

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
