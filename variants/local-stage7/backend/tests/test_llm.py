import json

import httpx
import pytest

from app.core.config import Settings
from app.core.llm import SparkAPIError, SparkHTTP, get_llm


def test_chat_sends_bearer_auth_and_returns_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret"
        payload = json.loads(request.content)
        assert payload["model"] == "SparkLite"
        assert payload["messages"] == [{"role": "user", "content": "你好"}]
        assert payload["stream"] is False
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "你好呀"}}]}
        )

    llm = SparkHTTP("secret", "SparkLite", transport=httpx.MockTransport(handler))
    assert llm.chat("你好") == "你好呀"


@pytest.mark.asyncio
async def test_chat_stream_yields_upstream_delta_tokens() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["stream"] is True
        body = (
            'data: {"choices":[{"delta":{"content":"你"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"好"}}]}\n\n'
            "data: [DONE]\n\n"
        )
        return httpx.Response(200, content=body.encode())

    llm = SparkHTTP("secret", "SparkLite", transport=httpx.MockTransport(handler))
    assert [token async for token in llm.chat_stream("你好")] == ["你", "好"]


def test_chat_raises_typed_error_instead_of_fake_text() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(503, json={"error": {"message": "busy"}})
    )
    with pytest.raises(SparkAPIError, match="busy"):
        SparkHTTP("secret", "SparkLite", transport=transport).chat("hello")


def test_chat_wraps_network_failure_as_typed_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    with pytest.raises(SparkAPIError, match="offline"):
        SparkHTTP("secret", "SparkLite", transport=httpx.MockTransport(handler)).chat(
            "hello"
        )


@pytest.mark.asyncio
async def test_chat_stream_rejects_malformed_upstream_event() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=b"data: not-json\n\n")
    )
    llm = SparkHTTP("secret", "SparkLite", transport=transport)
    with pytest.raises(SparkAPIError, match="Invalid Spark stream event"):
        _ = [token async for token in llm.chat_stream("hello")]


def test_get_llm_uses_configured_level() -> None:
    settings = Settings(
        _env_file=None,
        spark_api_key="legacy",
        spark_api_password="openai-password",
        spark_timeout_seconds=135,
        secret_key="x" * 32,
    )
    assert get_llm("high", settings).api_key == "openai-password"
    assert get_llm("high", settings).model == "generalv3.5"
    assert get_llm("medium", settings).model == "generalv3"
    assert get_llm("low", settings).model == "lite"
    assert get_llm("high", settings).timeout == 135
