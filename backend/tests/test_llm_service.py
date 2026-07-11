import asyncio
import errno

import pytest

from app.llm.service import LLMService
from app.llm.spark import (
    SparkConfigurationError,
    SparkEmptyResponseError,
    SparkStreamError,
)


class ScriptedClient:
    def __init__(self, attempts):
        self.attempts = list(attempts)
        self.calls = []

    async def stream(self, messages_or_prompt, model):
        self.calls.append((messages_or_prompt, model))
        outcome = self.attempts.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        for item in outcome:
            if isinstance(item, BaseException):
                raise item
            yield item


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["lite", "pro", "max"])
async def test_stream_forwards_chunks_and_selected_model(model):
    prompt = "hello"
    client = ScriptedClient([["a", "bc", "d"]])
    service = LLMService(client=client)

    chunks = [chunk async for chunk in service.stream(prompt, model=model)]

    assert chunks == ["a", "bc", "d"]
    assert client.calls == [(prompt, model)]


@pytest.mark.asyncio
async def test_non_string_prompt_is_rejected_explicitly():
    client = ScriptedClient([["unused"]])

    with pytest.raises(TypeError, match="prompt must be a string"):
        await LLMService(client=client).complete([{"content": "hello"}])

    assert client.calls == []


@pytest.mark.asyncio
async def test_complete_collects_stream_once():
    client = ScriptedClient([["hello", " world"]])

    result = await LLMService(client=client).complete("prompt", model="pro")

    assert result == "hello world"
    assert client.calls == [("prompt", "pro")]


@pytest.mark.asyncio
async def test_each_attempt_has_one_timeout_covering_all_chunks():
    class SlowClient:
        async def stream(self, messages_or_prompt, model):
            yield "first"
            await asyncio.sleep(1)
            yield "late"

    stream = LLMService(client=SlowClient()).stream("prompt", timeout_seconds=0.01)
    assert await anext(stream) == "first"

    with pytest.raises(TimeoutError):
        await anext(stream)


@pytest.mark.asyncio
async def test_timeout_before_first_chunk_is_not_retried():
    delays = []

    async def record_sleep(delay):
        delays.append(delay)

    class SlowClient:
        def __init__(self):
            self.calls = 0

        async def stream(self, messages_or_prompt, model):
            self.calls += 1
            await asyncio.sleep(1)
            yield "late"

    client = SlowClient()

    with pytest.raises(TimeoutError):
        await LLMService(client=client, sleep=record_sleep).complete(
            "prompt", timeout_seconds=0.01
        )

    assert client.calls == 1
    assert delays == []


@pytest.mark.asyncio
async def test_transient_network_errors_retry_with_exponential_backoff():
    first = SparkStreamError("request failed")
    first.__cause__ = ConnectionError("socket closed")
    second = OSError(errno.ENETUNREACH, "network unavailable")
    client = ScriptedClient([first, second, ["ok"]])
    delays = []

    async def record_sleep(delay):
        delays.append(delay)

    result = await LLMService(client=client, sleep=record_sleep).complete("prompt")

    assert result == "ok"
    assert len(client.calls) == 3
    assert delays == [1, 2]


@pytest.mark.asyncio
async def test_synchronous_stream_creation_connection_error_is_retried():
    class CreationFailingClient:
        def __init__(self):
            self.calls = 0

        def stream(self, messages_or_prompt, model):
            self.calls += 1
            if self.calls == 1:
                raise ConnectionError("connection refused")

            async def chunks():
                yield "ok"

            return chunks()

    client = CreationFailingClient()

    result = await LLMService(
        client=client, sleep=lambda _: asyncio.sleep(0)
    ).complete("prompt")

    assert result == "ok"
    assert client.calls == 2


@pytest.mark.asyncio
async def test_transient_network_error_is_raised_after_retries_are_exhausted():
    errors = [ConnectionError(f"failure {number}") for number in range(3)]
    client = ScriptedClient(errors)

    with pytest.raises(ConnectionError, match="failure 2"):
        await LLMService(client=client, sleep=lambda _: asyncio.sleep(0)).complete(
            "prompt"
        )

    assert len(client.calls) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error", [PermissionError("access denied"), FileNotFoundError("missing file")]
)
async def test_non_network_os_errors_are_not_retried(error):
    client = ScriptedClient([error])

    with pytest.raises(type(error), match=str(error)):
        await LLMService(client=client).complete("prompt")

    assert len(client.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        SparkConfigurationError("bad credentials"),
        ValueError("unknown model"),
        SparkEmptyResponseError("empty response"),
    ],
)
async def test_non_transient_errors_are_not_retried(error):
    client = ScriptedClient([error])

    with pytest.raises(type(error), match=str(error)):
        await LLMService(client=client).complete("prompt")

    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_cancellation_is_not_retried_or_swallowed():
    started = asyncio.Event()

    class BlockingClient:
        def __init__(self):
            self.calls = 0

        async def stream(self, messages_or_prompt, model):
            self.calls += 1
            started.set()
            await asyncio.Event().wait()
            yield "unreachable"

    client = BlockingClient()
    pending = asyncio.create_task(LLMService(client=client).complete("prompt"))
    await started.wait()
    pending.cancel()

    with pytest.raises(asyncio.CancelledError):
        await pending

    assert client.calls == 1


@pytest.mark.asyncio
async def test_error_after_a_chunk_is_not_retried_to_avoid_duplicate_text():
    error = ConnectionError("stream interrupted")
    client = ScriptedClient([["partial", error], ["replacement"]])
    stream = LLMService(client=client).stream("prompt")

    assert await anext(stream) == "partial"
    with pytest.raises(ConnectionError, match="stream interrupted"):
        await anext(stream)

    assert len(client.calls) == 1


class ClosableIterator:
    def __init__(self, items=None, wait_forever=False, close_error=None):
        self.items = list(items or [])
        self.wait_forever = wait_forever
        self.close_error = close_error
        self.close_calls = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.items:
            item = self.items.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item
        if self.wait_forever:
            await asyncio.Event().wait()
        raise StopAsyncIteration

    async def aclose(self):
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error


class IteratorClient:
    def __init__(self, iterators):
        self.iterators = list(iterators)
        self.calls = 0

    def stream(self, prompt, model):
        iterator = self.iterators[self.calls]
        self.calls += 1
        return iterator


@pytest.mark.asyncio
async def test_timeout_closes_underlying_iterator():
    iterator = ClosableIterator(wait_forever=True)

    with pytest.raises(TimeoutError):
        await LLMService(client=IteratorClient([iterator])).complete(
            "prompt", timeout_seconds=0.01
        )

    assert iterator.close_calls == 1


@pytest.mark.asyncio
async def test_every_retry_attempt_closes_its_iterator():
    first = ClosableIterator([ConnectionError("reset")])
    second = ClosableIterator(["ok"])
    service = LLMService(
        client=IteratorClient([first, second]), sleep=lambda _: asyncio.sleep(0)
    )

    assert await service.complete("prompt") == "ok"
    assert first.close_calls == 1
    assert second.close_calls == 1


@pytest.mark.asyncio
async def test_cancellation_closes_underlying_iterator():
    iterator = ClosableIterator(wait_forever=True)
    pending = asyncio.create_task(
        LLMService(client=IteratorClient([iterator])).complete("prompt")
    )
    await asyncio.sleep(0)
    pending.cancel()

    with pytest.raises(asyncio.CancelledError):
        await pending

    assert iterator.close_calls == 1


@pytest.mark.asyncio
async def test_caller_closing_stream_early_closes_underlying_iterator():
    iterator = ClosableIterator(["first", "second"])
    stream = LLMService(client=IteratorClient([iterator])).stream("prompt")
    assert await anext(stream) == "first"

    await stream.aclose()

    assert iterator.close_calls == 1


@pytest.mark.asyncio
async def test_partial_output_error_closes_underlying_iterator():
    iterator = ClosableIterator(["partial", ConnectionError("reset")])
    stream = LLMService(client=IteratorClient([iterator])).stream("prompt")
    assert await anext(stream) == "partial"

    with pytest.raises(ConnectionError, match="reset"):
        await anext(stream)

    assert iterator.close_calls == 1


@pytest.mark.asyncio
async def test_cleanup_failures_do_not_replace_primary_stream_error():
    primary = ConnectionError("primary failure")
    iterator = ClosableIterator(
        ["partial", primary], close_error=RuntimeError("iterator close")
    )

    class DistinctSource:
        def __init__(self):
            self.close_calls = 0

        def __aiter__(self):
            return iterator

        async def aclose(self):
            self.close_calls += 1
            raise RuntimeError("source close")

    source = DistinctSource()
    client = IteratorClient([source])

    with pytest.raises(ConnectionError, match="primary failure"):
        await LLMService(client=client, sleep=lambda _: asyncio.sleep(0)).complete(
            "prompt"
        )

    assert iterator.close_calls == 1
    assert source.close_calls == 1
