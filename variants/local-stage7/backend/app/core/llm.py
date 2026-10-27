from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class SparkAPIError(RuntimeError):
    """讯飞星火请求或响应协议错误。"""


# 在请求失败时按这个顺序回退到更便宜的模型
_FALLBACK_CHAIN = {
    "high": ["high", "medium", "low"],
    "medium": ["medium", "low"],
    "low": ["low"],
}


class SparkHTTP:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str = "https://spark-api-open.xf-yun.com/v1/chat/completions",
        timeout: float = 60.0,
        transport: httpx.BaseTransport | httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.transport = transport

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, prompt: str, max_tokens: int, *, stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": stream,
        }

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
            error = payload.get("error", payload)
            return (
                str(error.get("message", error))
                if isinstance(error, dict)
                else str(error)
            )
        except (ValueError, AttributeError):
            return response.text or f"HTTP {response.status_code}"

    def chat(self, prompt: str, max_tokens: int = 2048) -> str:
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.post(
                    self.base_url,
                    headers=self.headers,
                    json=self._payload(prompt, max_tokens, stream=False),
                )
            if not response.is_success:
                raise SparkAPIError(self._error_message(response))
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content:
                raise SparkAPIError("Spark response contains no message content")
            return content
        except SparkAPIError:
            raise
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise SparkAPIError(f"Spark request failed: {exc}") from exc

    async def chat_stream(
        self, prompt: str, max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, transport=self.transport
            ) as client:
                async with client.stream(
                    "POST",
                    self.base_url,
                    headers=self.headers,
                    json=self._payload(prompt, max_tokens, stream=True),
                ) as response:
                    if not response.is_success:
                        await response.aread()
                        raise SparkAPIError(self._error_message(response))
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            return
                        try:
                            payload = json.loads(data)
                            token = payload["choices"][0]["delta"].get("content")
                        except (
                            json.JSONDecodeError,
                            KeyError,
                            IndexError,
                            TypeError,
                        ) as exc:
                            raise SparkAPIError(
                                f"Invalid Spark stream event: {data}"
                            ) from exc
                        if token:
                            yield token
        except SparkAPIError:
            raise
        except httpx.HTTPError as exc:
            raise SparkAPIError(f"Spark stream failed: {exc}") from exc


def get_llm(level: str, settings: Settings) -> "SparkLLMWithFallback":
    """Return an LLM client that auto-falls-back on AppIdNoAuthError.

    Many Spark API keys only have permission for some tiers. If the requested
    tier is rejected, we transparently retry with the next cheaper tier so
    the user never sees a 503 just because of a billing/permission issue.
    """
    primary = SparkHTTP(
        settings.spark_bearer_token,
        settings.model_for(level),
        base_url=settings.spark_base_url,
        timeout=settings.spark_timeout_seconds,
    )
    fallbacks = []
    for fb_level in _FALLBACK_CHAIN.get(level, [level])[1:]:
        fallbacks.append(
            SparkHTTP(
                settings.spark_bearer_token,
                settings.model_for(fb_level),
                base_url=settings.spark_base_url,
                timeout=settings.spark_timeout_seconds,
            )
        )
    return SparkLLMWithFallback(primary, fallbacks)


class SparkLLMWithFallback:
    """Wrap a primary SparkHTTP and a list of fallbacks.

    On AppIdNoAuthError, try the next fallback. On any other error, raise.
    Streaming uses the first model that successfully answers the first token.
    """

    def __init__(self, primary: SparkHTTP, fallbacks: list[SparkHTTP]) -> None:
        self._primary = primary
        self._fallbacks = fallbacks
        self.model = primary.model

    def _is_auth_error(self, exc: Exception) -> bool:
        msg = str(exc)
        return (
            "AppIdNoAuthError" in msg
            or "权限" in msg
            or "授权" in msg
            or "Unauthorized" in msg
            or "403" in msg
        )

    def chat(self, prompt: str, max_tokens: int = 2048) -> str:
        last_exc: Exception | None = None
        for client in [self._primary, *self._fallbacks]:
            try:
                return client.chat(prompt, max_tokens)
            except SparkAPIError as exc:
                last_exc = exc
                if not self._is_auth_error(exc):
                    raise
                logger.warning(
                    "Spark model %s rejected (%s) - falling back", client.model, exc
                )
        if last_exc is not None:
            raise last_exc
        raise SparkAPIError("No LLM client available")

    async def chat_stream(
        self, prompt: str, max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        # For streaming we commit to whichever model returns the first token successfully.
        # Try primary first; on auth error at any point, abandon the stream and retry with
        # the next fallback using a non-streaming chat() instead (simpler, no partial state).
        try:
            async for token in self._primary.chat_stream(prompt, max_tokens):
                yield token
            return
        except SparkAPIError as exc:
            if not self._is_auth_error(exc):
                raise
            logger.warning(
                "Spark model %s stream rejected (%s) - falling back to non-stream",
                self._primary.model,
                exc,
            )
        for client in self._fallbacks:
            try:
                text = client.chat(prompt, max_tokens)
                # Yield in ~80-char chunks to balance responsiveness and SSE round-trip cost
                chunk_size = 80
                for i in range(0, len(text), chunk_size):
                    yield text[i : i + chunk_size]
                return
            except SparkAPIError as exc:
                if not self._is_auth_error(exc):
                    raise
                logger.warning(
                    "Spark fallback %s also rejected (%s)", client.model, exc
                )
        raise SparkAPIError("All Spark fallbacks exhausted")
