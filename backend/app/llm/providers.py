import asyncio
import json
import logging
from collections.abc import AsyncGenerator, Iterable
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class NamedProvider:
    def __init__(self, name: str, provider: Any) -> None:
        self.name = name
        self.provider = provider

    def stream(self, prompt: str, model: str | None = None):
        return self.provider.stream(prompt, model)


class ProviderExhaustedError(RuntimeError):
    def __init__(self, failures: dict[str, str]):
        super().__init__("all configured model providers are unavailable")
        self.failures = failures


class OpenAICompatibleProvider:
    def __init__(
        self, *, name: str, base_url: str, api_key: str, model: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._client = client

    async def stream(self, prompt: str, model: str | None = None) -> AsyncGenerator[str, None]:
        if not self.base_url or not self.model or not self.api_key:
            raise RuntimeError(f"{self.name} is not configured")
        owned_client = self._client is None
        client = self._client or httpx.AsyncClient(
            timeout=httpx.Timeout(60, connect=10),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        try:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        payload = json.loads(data)
                        delta = payload["choices"][0].get("delta", {})
                        content = delta.get("content")
                    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
                        continue
                    if isinstance(content, str) and content:
                        yield content
        finally:
            if owned_client:
                await client.aclose()


class ProviderRouter:
    def __init__(self, providers: Iterable[Any]) -> None:
        self.providers = list(providers)
        self.last_provider: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.providers)

    async def stream(self, prompt: str, model: str | None = None) -> AsyncGenerator[str, None]:
        failures: dict[str, str] = {}
        for provider in self.providers:
            name = getattr(provider, "name", provider.__class__.__name__)
            yielded = False
            source = None
            try:
                source = provider.stream(prompt, model)
                async for chunk in source:
                    yielded = True
                    self.last_provider = name
                    yield chunk
                if yielded:
                    return
                failures[name] = "empty response"
            except (asyncio.CancelledError, GeneratorExit):
                raise
            except Exception as exc:
                if yielded:
                    raise
                failures[name] = f"{type(exc).__name__}: {exc}"
                logger.warning("Model provider %s unavailable; trying fallback", name)
            finally:
                close = getattr(source, "aclose", None)
                if close is not None:
                    await close()
        raise ProviderExhaustedError(failures)


def build_provider_router(settings: Any, spark_client: Any) -> ProviderRouter:
    providers: list[Any] = []
    if all(str(getattr(settings, field, "")).strip() for field in (
        "spark_app_id", "spark_api_key", "spark_api_secret",
    )):
        providers.append(NamedProvider("spark", spark_client))

    def add_openai(name: str, key_field: str, base_field: str, model_field: str) -> None:
        api_key = str(getattr(settings, key_field, "")).strip()
        if api_key:
            providers.append(OpenAICompatibleProvider(
                name=name,
                api_key=api_key,
                base_url=str(getattr(settings, base_field)),
                model=str(getattr(settings, model_field)),
            ))

    add_openai("zhipu-free", "zhipu_api_key", "zhipu_base_url", "zhipu_model")
    add_openai("ant-bailing", "ant_bailing_api_key", "ant_bailing_base_url", "ant_bailing_model")
    add_openai("agnes", "agnes_api_key", "agnes_base_url", "agnes_model")
    if bool(getattr(settings, "ollama_enabled", False)):
        providers.append(OpenAICompatibleProvider(
            name="ollama-local", api_key="ollama",
            base_url=str(getattr(settings, "ollama_base_url")),
            model=str(getattr(settings, "ollama_model")),
        ))
    return ProviderRouter(providers)
