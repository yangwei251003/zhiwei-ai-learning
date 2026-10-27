from __future__ import annotations

import asyncio

from app.core.config import Settings
from app.core.llm import get_llm


async def main() -> None:
    settings = Settings()
    llm = get_llm("low", settings)
    reply = llm.chat("Reply only OK.", max_tokens=8)
    print(f"SYNC_OK chars={len(reply)}")
    tokens = [token async for token in llm.chat_stream("Reply only OK.", max_tokens=8)]
    print(f"STREAM_OK chunks={len(tokens)} chars={sum(map(len, tokens))}")


if __name__ == "__main__":
    asyncio.run(main())
