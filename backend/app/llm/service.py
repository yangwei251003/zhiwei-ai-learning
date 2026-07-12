import asyncio
import errno
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

from app.llm.spark import (
    SparkConfigurationError,
    SparkEmptyResponseError,
    SparkLLM,
)
from app.llm.providers import build_provider_router


Sleep = Callable[[float], Awaitable[None]]
logger = logging.getLogger(__name__)
_TRANSIENT_NETWORK_ERRNOS = frozenset(
    {
        errno.ECONNREFUSED,
        errno.ECONNRESET,
        errno.EHOSTUNREACH,
        errno.ENETUNREACH,
        errno.EPIPE,
        errno.ETIMEDOUT,
    }
)


class LLMService:
    def __init__(self, client: Any | None = None, sleep: Sleep = asyncio.sleep) -> None:
        if client is None:
            from app.core import get_settings
            settings = get_settings()
            self._client = build_provider_router(settings, SparkLLM())
        else:
            self._client = client
        self._sleep = sleep

    async def stream(
        self,
        prompt: str,
        model: str = "max",
        timeout_seconds: float = 60,
    ) -> AsyncGenerator[str, None]:
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string")

        for retry_number in range(3):
            yielded = False
            deadline = asyncio.get_running_loop().time() + timeout_seconds
            primary_error: BaseException | None = None
            close_targets: list[Any] = []
            close_target_ids: set[int] = set()
            should_retry = False

            def register_close_target(target: Any) -> None:
                if id(target) in close_target_ids:
                    return
                if callable(getattr(target, "aclose", None)):
                    close_target_ids.add(id(target))
                    close_targets.append(target)

            try:
                source = self._client.stream(prompt, model)
                register_close_target(source)
                iterator = source.__aiter__()
                register_close_target(iterator)
                while True:
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
                        raise TimeoutError

                    try:
                        async with asyncio.timeout(remaining):
                            chunk = await anext(iterator)
                    except StopAsyncIteration:
                        return

                    yielded = True
                    yield chunk
            except BaseException as exc:
                primary_error = exc
                if isinstance(exc, (asyncio.CancelledError, GeneratorExit)):
                    raise
                if yielded or retry_number == 2 or not self._is_transient(exc):
                    raise
                should_retry = True
            finally:
                await self._close_targets(close_targets, primary_error)

            if should_retry:
                await self._sleep(2**retry_number)

    async def complete(
        self,
        prompt: str,
        model: str = "max",
        timeout_seconds: float = 60,
    ) -> str:
        return "".join(
            [
                chunk
                async for chunk in self.stream(
                    prompt,
                    model=model,
                    timeout_seconds=timeout_seconds,
                )
            ]
        )

    @staticmethod
    async def _close_targets(
        targets: list[Any], primary_error: BaseException | None
    ) -> None:
        first_cleanup_error: BaseException | None = None
        for target in targets:
            try:
                await target.aclose()
            except BaseException as cleanup_error:
                if primary_error is None and first_cleanup_error is None:
                    first_cleanup_error = cleanup_error
                else:
                    logger.warning(
                        "LLM stream cleanup failed after a primary error",
                        exc_info=cleanup_error,
                    )

        if primary_error is None and first_cleanup_error is not None:
            raise first_cleanup_error

    @staticmethod
    def _is_transient(error: BaseException) -> bool:
        current: BaseException | None = error
        seen: set[int] = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if isinstance(current, TimeoutError):
                return False
            if isinstance(
                current,
                (SparkConfigurationError, SparkEmptyResponseError, ValueError),
            ):
                return False
            if isinstance(current, ConnectionError):
                return True
            if isinstance(current, OSError) and current.errno in _TRANSIENT_NETWORK_ERRNOS:
                return True
            current = current.__cause__ or current.__context__
        return False
