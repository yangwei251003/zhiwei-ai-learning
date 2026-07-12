import json

import httpx
import pytest

from app.llm.providers import OpenAICompatibleProvider, ProviderExhaustedError, ProviderRouter, build_provider_router


class ScriptedProvider:
    def __init__(self, name, items):
        self.name = name
        self.items = list(items)
        self.calls = 0

    async def stream(self, prompt, model=None):
        self.calls += 1
        for item in self.items:
            if isinstance(item, BaseException):
                raise item
            yield item


@pytest.mark.asyncio
async def test_router_falls_back_when_provider_fails_before_first_token():
    spark = ScriptedProvider("spark", [RuntimeError("quota exhausted")])
    zhipu = ScriptedProvider("zhipu-free", ["免", "费"])
    router = ProviderRouter([spark, zhipu])

    chunks = [chunk async for chunk in router.stream("hello")]

    assert chunks == ["免", "费"]
    assert router.last_provider == "zhipu-free"
    assert spark.calls == zhipu.calls == 1


@pytest.mark.asyncio
async def test_router_never_switches_after_partial_output():
    spark = ScriptedProvider("spark", ["partial", RuntimeError("disconnect")])
    zhipu = ScriptedProvider("zhipu-free", ["replacement"])
    router = ProviderRouter([spark, zhipu])
    stream = router.stream("hello")

    assert await anext(stream) == "partial"
    with pytest.raises(RuntimeError, match="disconnect"):
        await anext(stream)
    assert zhipu.calls == 0


@pytest.mark.asyncio
async def test_router_reports_all_provider_failures_without_fake_text():
    router = ProviderRouter([
        ScriptedProvider("one", [RuntimeError("quota")]),
        ScriptedProvider("two", [RuntimeError("offline")]),
    ])
    with pytest.raises(ProviderExhaustedError) as info:
        await anext(router.stream("hello"))
    assert set(info.value.failures) == {"one", "two"}


@pytest.mark.asyncio
async def test_openai_compatible_provider_parses_streaming_sse():
    async def handler(request: httpx.Request):
        body = json.loads(request.content)
        assert body["model"] == "free-model"
        assert body["stream"] is True
        content = (
            'data: {"choices":[{"delta":{"content":"你"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"好"}}]}\n\n'
            'data: [DONE]\n\n'
        )
        return httpx.Response(200, text=content, headers={"content-type": "text/event-stream"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        name="free", base_url="https://example.test/v1", api_key="secret",
        model="free-model", client=client,
    )
    assert [chunk async for chunk in provider.stream("hello")] == ["你", "好"]
    await client.aclose()


def test_default_router_uses_cloud_then_free_then_local_order():
    class Settings:
        spark_app_id = "app"; spark_api_key = "key"; spark_api_secret = "secret"
        zhipu_api_key = "zhipu"; zhipu_base_url = "https://open.bigmodel.cn/api/paas/v4"; zhipu_model = "glm-4.7-flash"
        ant_bailing_api_key = "ant"; ant_bailing_base_url = "https://api.ant-ling.com/v1"; ant_bailing_model = "Ling-2.6-flash"
        agnes_api_key = "agnes"; agnes_base_url = "https://apihub.agnes-ai.com/v1"; agnes_model = "agnes-2.0-flash"
        ollama_enabled = True; ollama_base_url = "http://127.0.0.1:11434/v1"; ollama_model = "qwen2.5:3b"

    router = build_provider_router(Settings(), ScriptedProvider("spark-client", ["ok"]))

    assert [provider.name for provider in router.providers] == [
        "spark", "zhipu-free", "ant-bailing", "agnes", "ollama-local",
    ]
