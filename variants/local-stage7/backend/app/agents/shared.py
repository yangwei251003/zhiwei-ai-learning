from __future__ import annotations

import json
from typing import Any

from langgraph.config import get_stream_writer

from app.core.llm import SparkAPIError
from app.services.knowledge import RetrievalResult


def emit(event: dict[str, Any]) -> None:
    try:
        writer = get_stream_writer()
    except RuntimeError:
        return
    writer(event)


def parse_json_object(content: str) -> dict[str, Any]:
    candidate = content.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        candidate = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        value = None
    if value is not None:
        if not isinstance(value, dict):
            raise SparkAPIError("Spark response must be a JSON object")
        return value

    decoder = json.JSONDecoder()
    for index, character in enumerate(content):
        if character != "{":
            continue
        try:
            embedded, _ = decoder.raw_decode(content, index)
        except json.JSONDecodeError:
            continue
        if isinstance(embedded, dict):
            return embedded
    raise SparkAPIError("Spark response is not a valid JSON object")


def evidence_text(retrieval: RetrievalResult) -> str:
    if not retrieval.is_hit:
        return "知识库没有足够证据。回答必须明确包含“我不确定”，并建议用户补充资料。"
    return "\n\n".join(f"来源：{hit.source}\n{hit.content}" for hit in retrieval.hits)
