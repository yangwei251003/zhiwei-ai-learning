import asyncio
import queue
import threading
import time
from collections.abc import Iterator

import pytest

from app.llm.models import MODEL_REGISTRY, resolve_model
from app.llm.spark import (
    SparkConfigurationError,
    SparkEmptyResponseError,
    SparkLLM,
    SparkStreamError,
)


def blocking_sdk_process(app_id, api_key, api_secret, prompt, model, output):
    output.put(("chunk", "first"))
    while True:
        time.sleep(1)


def configured_llm(stream_factory):
    return SparkLLM(
        app_id="app-id",
        api_key="api-key",
        api_secret="api-secret",
        stream_factory=stream_factory,
    )


def test_model_registry_matches_spark_3_endpoints():
    assert set(MODEL_REGISTRY) == {"lite", "pro", "max"}
    assert (MODEL_REGISTRY["lite"].api_url, MODEL_REGISTRY["lite"].domain) == (
        "wss://spark-api.xf-yun.com/v1.1/chat",
        "general",
    )
    assert (MODEL_REGISTRY["pro"].api_url, MODEL_REGISTRY["pro"].domain) == (
        "wss://spark-api.xf-yun.com/v3.1/chat",
        "generalv3",
    )
    assert (MODEL_REGISTRY["max"].api_url, MODEL_REGISTRY["max"].domain) == (
        "wss://spark-api.xf-yun.com/v3.5/chat",
        "generalv3.5",
    )


def test_unknown_model_is_rejected():
    with pytest.raises(ValueError, match="Unknown Spark model"):
        resolve_model("ultra")


@pytest.mark.asyncio
async def test_sync_sdk_chunks_are_forwarded_without_rechunking():
    factory_thread = None
    consumed_threads = []

    def stream_factory(prompt, model):
        nonlocal factory_thread
        factory_thread = threading.get_ident()
        assert prompt == "hello"
        assert model.name == "pro"

        def chunks():
            for chunk in ["a", "bc", "d"]:
                consumed_threads.append(threading.get_ident())
                yield chunk

        return chunks()

    main_thread = threading.get_ident()
    chunks = [chunk async for chunk in configured_llm(stream_factory).stream("hello", "pro")]

    assert chunks == ["a", "bc", "d"]
    assert factory_thread != main_thread
    assert consumed_threads and all(thread != main_thread for thread in consumed_threads)


@pytest.mark.asyncio
async def test_async_factory_chunks_are_supported():
    async def stream_factory(prompt, model):
        for chunk in ["a", "bc", "d"]:
            yield chunk

    chunks = [chunk async for chunk in configured_llm(stream_factory).stream("hello")]

    assert chunks == ["a", "bc", "d"]


@pytest.mark.asyncio
async def test_missing_configuration_is_explicit():
    llm = SparkLLM(app_id="", api_key="", api_secret="", stream_factory=lambda *_: iter(()))

    with pytest.raises(SparkConfigurationError, match="credentials are not configured"):
        await anext(llm.stream("hello"))


@pytest.mark.asyncio
async def test_sdk_failure_is_wrapped_with_cause():
    sdk_error = OSError("socket closed")

    def broken_stream(*_):
        raise sdk_error

    with pytest.raises(SparkStreamError, match="streaming request failed") as exc_info:
        await anext(configured_llm(broken_stream).stream("hello"))

    assert exc_info.value.__cause__ is sdk_error


@pytest.mark.asyncio
async def test_empty_response_is_explicit():
    llm = configured_llm(lambda *_: iter(["", None]))

    with pytest.raises(SparkEmptyResponseError, match="empty response"):
        await anext(llm.stream("hello"))


@pytest.mark.asyncio
async def test_cancellation_cleans_up_blocking_generator_on_its_worker_thread():
    started = threading.Event()
    release = threading.Event()
    cleaned = threading.Event()
    cleanup_thread = None
    close_threads = []

    def blocking_chunks():
        nonlocal cleanup_thread
        try:
            started.set()
            release.wait(timeout=2)
            yield "too late"
        finally:
            cleanup_thread = threading.get_ident()
            cleaned.set()

    class TrackingIterator:
        def __init__(self):
            self.generator = blocking_chunks()

        def __iter__(self):
            return self

        def __next__(self):
            return next(self.generator)

        def close(self):
            close_threads.append(threading.get_ident())
            self.generator.close()

    stream = configured_llm(lambda *_: TrackingIterator()).stream("hello")
    pending_chunk = asyncio.create_task(anext(stream))
    assert await asyncio.to_thread(started.wait, 0.5)

    pending_chunk.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(pending_chunk, timeout=0.5)

    release.set()
    assert await asyncio.to_thread(cleaned.wait, 0.5)
    assert cleanup_thread != threading.get_ident()
    assert close_threads and all(
        close_thread != threading.get_ident() for close_thread in close_threads
    )
    assert not any(
        thread.name == "spark-stream" and thread.is_alive()
        for thread in threading.enumerate()
    )


class FailingIterator(Iterator[str]):
    def __next__(self) -> str:
        raise OSError("iteration failed")

    def close(self) -> None:
        raise KeyError("cleanup failed")


@pytest.mark.asyncio
async def test_sync_cleanup_failure_does_not_replace_stream_failure():
    stream = configured_llm(lambda *_: FailingIterator()).stream("hello")

    with pytest.raises(SparkStreamError, match="streaming request failed") as exc_info:
        await anext(stream)

    assert isinstance(exc_info.value.__cause__, OSError)


@pytest.mark.asyncio
async def test_async_cleanup_failure_does_not_replace_stream_failure():
    class FailingAsyncIterator:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise OSError("iteration failed")

        async def aclose(self):
            raise RuntimeError("cleanup failed")

    stream = configured_llm(lambda *_: FailingAsyncIterator()).stream("hello")

    with pytest.raises(SparkStreamError, match="streaming request failed") as exc_info:
        await anext(stream)

    assert isinstance(exc_info.value.__cause__, OSError)


@pytest.mark.asyncio
async def test_async_cleanup_failure_does_not_replace_cancellation():
    class CancellableAsyncIterator:
        def __init__(self):
            self.first = True

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.first:
                self.first = False
                return "first"
            await asyncio.Event().wait()

        async def aclose(self):
            raise RuntimeError("cleanup failed")

    stream = configured_llm(lambda *_: CancellableAsyncIterator()).stream("hello")
    assert await anext(stream) == "first"
    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    pending.cancel()

    with pytest.raises(asyncio.CancelledError):
        await pending


@pytest.mark.asyncio
async def test_sdk_process_is_terminated_and_joined_on_cancellation():
    llm = SparkLLM(
        app_id="app-id",
        api_key="api-key",
        api_secret="api-secret",
        process_target=blocking_sdk_process,
    )
    stream = llm.stream("hello")
    assert await asyncio.wait_for(anext(stream), timeout=3) == "first"

    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0.05)
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending

    process = llm._sdk_process
    assert process is not None
    assert not process.is_alive()
    assert process.exitcode is not None


class FailingCleanupQueue:
    def __init__(self, items, calls):
        self.items = list(items)
        self.calls = calls

    def get_nowait(self):
        if self.items:
            return self.items.pop(0)
        raise queue.Empty

    def cancel_join_thread(self):
        self.calls.append("cancel_join_thread")
        raise RuntimeError("cancel join failed")

    def close(self):
        self.calls.append("queue_close")
        raise RuntimeError("queue close failed")


class FailingCleanupProcess:
    def __init__(self, calls):
        self.calls = calls

    def start(self):
        self.calls.append("start")

    def is_alive(self):
        return True

    def terminate(self):
        self.calls.append("terminate")
        raise RuntimeError("terminate failed")

    def join(self, timeout=None):
        self.calls.append("join")
        raise RuntimeError("join failed")

    def kill(self):
        self.calls.append("kill")
        raise RuntimeError("kill failed")


class FailingCleanupContext:
    def __init__(self, items, calls):
        self.output = FailingCleanupQueue(items, calls)
        self.process = FailingCleanupProcess(calls)

    def Queue(self):
        return self.output

    def Process(self, **kwargs):
        return self.process


def install_failing_process_context(monkeypatch, items):
    calls = []
    context = FailingCleanupContext(items, calls)
    monkeypatch.setattr(
        "app.llm.spark.multiprocessing.get_context", lambda _: context
    )
    llm = SparkLLM(app_id="app-id", api_key="api-key", api_secret="api-secret")
    return llm, calls


def assert_all_process_cleanup_was_attempted(calls):
    for expected in ("terminate", "join", "kill", "cancel_join_thread", "queue_close"):
        assert expected in calls


@pytest.mark.asyncio
async def test_process_cleanup_failures_do_not_replace_spark_error(monkeypatch):
    llm, calls = install_failing_process_context(
        monkeypatch, [("error", "primary sdk failure")]
    )

    with pytest.raises(SparkStreamError, match="primary sdk failure"):
        await anext(llm.stream("hello"))

    assert_all_process_cleanup_was_attempted(calls)


@pytest.mark.asyncio
async def test_process_cleanup_failures_do_not_replace_cancellation(monkeypatch):
    llm, calls = install_failing_process_context(monkeypatch, [])
    pending = asyncio.create_task(anext(llm.stream("hello")))
    await asyncio.sleep(0)
    pending.cancel()

    with pytest.raises(asyncio.CancelledError):
        await pending

    assert_all_process_cleanup_was_attempted(calls)


@pytest.mark.asyncio
async def test_process_cleanup_failures_do_not_replace_generator_close(monkeypatch):
    llm, calls = install_failing_process_context(monkeypatch, [("chunk", "first")])
    stream = llm.stream("hello")
    assert await anext(stream) == "first"

    await stream.aclose()

    assert_all_process_cleanup_was_attempted(calls)


@pytest.mark.asyncio
async def test_process_cleanup_failure_without_primary_error_is_explicit(monkeypatch):
    llm, calls = install_failing_process_context(monkeypatch, [("done", None)])

    with pytest.raises(SparkStreamError, match="cleanup failed"):
        await anext(llm.stream("hello"))

    assert_all_process_cleanup_was_attempted(calls)


class CleanQueue:
    def __init__(self, items):
        self.items = list(items)

    def get_nowait(self):
        if self.items:
            return self.items.pop(0)
        raise queue.Empty

    def cancel_join_thread(self):
        pass

    def close(self):
        pass


class SlowLifecycleProcess:
    def __init__(self, start_delay=0, join_delay=0):
        self.start_delay = start_delay
        self.join_delay = join_delay
        self.alive = True

    def start(self):
        time.sleep(self.start_delay)

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.alive = False

    def join(self, timeout=None):
        time.sleep(self.join_delay)

    def kill(self):
        self.alive = False


class SlowLifecycleContext:
    def __init__(self, process, items):
        self.process = process
        self.output = CleanQueue(items)

    def Queue(self):
        return self.output

    def Process(self, **kwargs):
        return self.process


async def heartbeat(counter, stopped):
    while not stopped.is_set():
        counter[0] += 1
        await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_slow_process_start_does_not_block_event_loop(monkeypatch):
    process = SlowLifecycleProcess(start_delay=0.25)
    context = SlowLifecycleContext(process, [("done", None)])
    monkeypatch.setattr(
        "app.llm.spark.multiprocessing.get_context", lambda _: context
    )
    llm = SparkLLM(app_id="app-id", api_key="api-key", api_secret="api-secret")
    ticks = [0]
    stopped = asyncio.Event()
    pulse = asyncio.create_task(heartbeat(ticks, stopped))

    with pytest.raises(SparkEmptyResponseError):
        await anext(llm.stream("hello"))

    stopped.set()
    await pulse
    assert ticks[0] >= 10


@pytest.mark.asyncio
async def test_slow_process_cleanup_during_cancellation_does_not_block_event_loop(
    monkeypatch,
):
    process = SlowLifecycleProcess(join_delay=0.25)
    context = SlowLifecycleContext(process, [])
    monkeypatch.setattr(
        "app.llm.spark.multiprocessing.get_context", lambda _: context
    )
    llm = SparkLLM(app_id="app-id", api_key="api-key", api_secret="api-secret")
    pending = asyncio.create_task(anext(llm.stream("hello")))
    await asyncio.sleep(0.02)
    ticks = [0]
    stopped = asyncio.Event()
    pulse = asyncio.create_task(heartbeat(ticks, stopped))

    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending

    stopped.set()
    await pulse
    assert ticks[0] >= 10
