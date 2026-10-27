import asyncio
import logging
import multiprocessing
import os
import queue as queue_module
import threading
from collections.abc import AsyncGenerator, AsyncIterator, Callable, Iterator, Mapping
from typing import Any

from app.llm.models import SparkModelConfig, resolve_model


class SparkError(RuntimeError):
    """Base error for Spark LLM streaming."""


class SparkConfigurationError(SparkError):
    """Raised when required credentials or the official SDK are unavailable."""


class SparkStreamError(SparkError):
    """Raised when the SDK streaming request fails."""


class SparkEmptyResponseError(SparkStreamError):
    """Raised when Spark completes without returning any text."""


StreamFactory = Callable[[str, SparkModelConfig], Any]
ProcessTarget = Callable[..., None]
_DONE = object()
logger = logging.getLogger(__name__)


def _start_process(process: Any) -> None:
    process.start()


def _cleanup_process(process: Any, output: Any) -> list[tuple[str, BaseException]]:
    cleanup_errors: list[tuple[str, BaseException]] = []

    def attempt(name: str, operation: Callable[[], Any]) -> Any:
        try:
            return operation()
        except BaseException as cleanup_error:
            cleanup_errors.append((name, cleanup_error))
            return None

    alive = attempt("is_alive", process.is_alive)
    if alive is not False:
        attempt("terminate", process.terminate)
    attempt("join", lambda: process.join(timeout=1))
    alive = attempt("is_alive_after_terminate", process.is_alive)
    if alive is not False:
        attempt("kill", process.kill)
        attempt("join_after_kill", lambda: process.join(timeout=1))
    attempt("cancel_join_thread", output.cancel_join_thread)
    attempt("queue_close", output.close)
    return cleanup_errors


def _sdk_process_main(
    app_id: str,
    api_key: str,
    api_secret: str,
    prompt: str,
    model: SparkModelConfig,
    output: Any,
) -> None:
    try:
        from sparkai.core.messages import HumanMessage
        from sparkai.llm.llm import ChatSparkLLM
    except ImportError as exc:
        output.put(("configuration_error", str(exc)))
        return

    try:
        client = ChatSparkLLM(
            spark_api_url=model.api_url,
            spark_app_id=app_id,
            spark_api_key=api_key,
            spark_api_secret=api_secret,
            spark_llm_domain=model.domain,
            streaming=True,
        )
        for chunk in client.stream([HumanMessage(content=prompt)], llm_output={}):
            text = SparkLLM._chunk_text(chunk)
            if text:
                output.put(("chunk", text))
    except BaseException as exc:
        output.put(("error", f"{type(exc).__name__}: {exc}"))
    finally:
        output.put(("done", None))


class SparkLLM:
    def __init__(
        self,
        app_id: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        stream_factory: StreamFactory | None = None,
        process_target: ProcessTarget | None = None,
    ) -> None:
        from app.core import get_settings

        settings = get_settings()
        self.app_id = (
            os.getenv("SPARK_APP_ID") or settings.spark_app_id
            if app_id is None else app_id
        )
        self.api_key = (
            os.getenv("SPARK_API_KEY") or settings.spark_api_key
            if api_key is None else api_key
        )
        self.api_secret = (
            os.getenv("SPARK_API_SECRET") or settings.spark_api_secret
            if api_secret is None else api_secret
        )
        self._stream_factory = stream_factory
        self._process_target = process_target or _sdk_process_main
        self._sdk_process: multiprocessing.Process | None = None

    def _validate_configuration(self) -> None:
        if not all(
            value.strip() for value in (self.app_id, self.api_key, self.api_secret)
        ):
            raise SparkConfigurationError("Spark credentials are not configured")

    async def stream(
        self, prompt: str, model: str = "lite"
    ) -> AsyncGenerator[str, None]:
        self._validate_configuration()
        model_config = resolve_model(model)

        yielded = False
        if self._stream_factory is None:
            process_stream = self._consume_sdk_process(prompt, model_config)
            try:
                async for text in process_stream:
                    yielded = True
                    yield text
            finally:
                await process_stream.aclose()
        else:
            try:
                source = await asyncio.to_thread(
                    self._stream_factory, prompt, model_config
                )
            except (SparkConfigurationError, asyncio.CancelledError):
                raise
            except Exception as exc:
                raise SparkStreamError("Spark streaming request failed") from exc

            if hasattr(source, "__aiter__"):
                async for text in self._consume_async(source):
                    yielded = True
                    yield text
            else:
                async for text in self._consume_sync(iter(source)):
                    yielded = True
                    yield text

        if not yielded:
            raise SparkEmptyResponseError("Spark returned an empty response")

    async def _consume_async(self, source: AsyncIterator[Any]) -> AsyncGenerator[str, None]:
        primary_error: BaseException | None = None
        try:
            async for chunk in source:
                text = self._chunk_text(chunk)
                if text:
                    yield text
        except BaseException as exc:
            primary_error = exc
            if isinstance(exc, (asyncio.CancelledError, GeneratorExit)):
                raise
            if isinstance(exc, SparkError):
                raise
            raise SparkStreamError("Spark streaming request failed") from exc
        finally:
            close = getattr(source, "aclose", None)
            if close is not None:
                try:
                    await close()
                except BaseException as cleanup_error:
                    if primary_error is None:
                        raise SparkStreamError("Spark stream cleanup failed") from cleanup_error
                    logger.warning(
                        "Spark async stream cleanup failed after a primary error",
                        exc_info=cleanup_error,
                    )

    async def _consume_sync(self, source: Iterator[Any]) -> AsyncGenerator[str, None]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[tuple[object, Any]] = asyncio.Queue()
        stopped = threading.Event()

        def send(kind: object, value: Any = None) -> None:
            if stopped.is_set():
                return
            try:
                loop.call_soon_threadsafe(queue.put_nowait, (kind, value))
            except RuntimeError:
                pass

        def consume() -> None:
            primary_error: BaseException | None = None
            try:
                for chunk in source:
                    if stopped.is_set():
                        break
                    send("chunk", chunk)
            except BaseException as exc:
                primary_error = exc
                send("error", exc)
            finally:
                close = getattr(source, "close", None)
                if close is not None:
                    try:
                        close()
                    except BaseException as cleanup_error:
                        if primary_error is None:
                            send("error", cleanup_error)
                        else:
                            logger.warning(
                                "Spark sync stream cleanup failed after a primary error",
                                exc_info=cleanup_error,
                            )
                send(_DONE)

        worker = threading.Thread(target=consume, name="spark-stream", daemon=True)
        worker.start()
        try:
            while True:
                kind, value = await queue.get()
                if kind is _DONE:
                    break
                if kind == "error":
                    if isinstance(value, SparkError):
                        raise value
                    raise SparkStreamError("Spark streaming request failed") from value
                text = self._chunk_text(value)
                if text:
                    yield text
        finally:
            stopped.set()

    async def _consume_sdk_process(
        self, prompt: str, model: SparkModelConfig
    ) -> AsyncGenerator[str, None]:
        context = multiprocessing.get_context("spawn")
        output = context.Queue()
        process = context.Process(
            target=self._process_target,
            args=(self.app_id, self.api_key, self.api_secret, prompt, model, output),
            name="spark-sdk-stream",
            daemon=True,
        )
        self._sdk_process = process
        dead_polls = 0
        primary_error: BaseException | None = None
        try:
            await asyncio.to_thread(_start_process, process)
            while True:
                try:
                    kind, value = output.get_nowait()
                    dead_polls = 0
                except queue_module.Empty:
                    if not process.is_alive():
                        dead_polls += 1
                        if dead_polls >= 10:
                            raise SparkStreamError(
                                "Spark SDK process exited without completing the stream"
                            )
                    await asyncio.sleep(0.01)
                    continue

                if kind == "done":
                    break
                if kind == "configuration_error":
                    raise SparkConfigurationError(
                        "The official spark-ai-python SDK is not installed"
                    )
                if kind == "error":
                    raise SparkStreamError(f"Spark streaming request failed: {value}")
                if kind == "chunk":
                    yield value
        except BaseException as exc:
            primary_error = exc
            raise
        finally:
            cleanup_errors = await asyncio.to_thread(
                _cleanup_process, process, output
            )

            if cleanup_errors:
                if primary_error is None:
                    details = ", ".join(name for name, _ in cleanup_errors)
                    raise SparkStreamError(
                        f"Spark SDK process cleanup failed: {details}"
                    ) from cleanup_errors[0][1]
                for name, cleanup_error in cleanup_errors:
                    logger.warning(
                        "Spark SDK process cleanup step %s failed after a primary error",
                        name,
                        exc_info=cleanup_error,
                    )

    @staticmethod
    def _chunk_text(chunk: Any) -> str | None:
        if chunk is None or isinstance(chunk, str):
            return chunk
        if isinstance(chunk, Mapping):
            content = chunk.get("content")
        else:
            content = getattr(chunk, "content", None)
        if content is None:
            return None
        if not isinstance(content, str):
            raise TypeError("Spark stream chunk content must be text")
        return content
