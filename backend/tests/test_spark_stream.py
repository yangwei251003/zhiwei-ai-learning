import asyncio
import os

import pytest
from dotenv import load_dotenv

from app.llm.spark import SparkLLM


load_dotenv()


def _credentials_available() -> bool:
    return all(
        (os.getenv(name) or "").strip()
        for name in ("SPARK_APP_ID", "SPARK_API_KEY", "SPARK_API_SECRET")
    )


@pytest.mark.asyncio
async def test_real_spark_stream():
    if not _credentials_available():
        pytest.skip("Spark credentials are not configured")

    llm = SparkLLM()
    stream = llm.stream("你好", model="max")
    chunks = []
    try:
        first = await asyncio.wait_for(anext(stream), timeout=20)
        chunks.append(first)
        print(first, end="", flush=True)

        async with asyncio.timeout(40):
            async for chunk in stream:
                chunks.append(chunk)
                print(chunk, end="", flush=True)
    finally:
        await stream.aclose()

    response = "".join(chunks).strip()
    assert response
    assert llm._sdk_process is not None
    assert not llm._sdk_process.is_alive()
    assert response not in {
        "这是一个模拟回复",
        "您好！我是AI学习助手，请问有什么可以帮助您？",
        "你好！我是AI学习助手，请问有什么可以帮助您？",
    }
