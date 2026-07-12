import json
from typing import Any


def extract_json_value(raw: str | dict | list) -> Any:
    """Decode the first complete JSON value from common LLM wrappers."""
    if isinstance(raw, (dict, list)):
        return raw
    if not isinstance(raw, str):
        raise TypeError("LLM output must be text or JSON")
    text = raw.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        text = text[first_newline + 1:] if first_newline >= 0 else text[3:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].rstrip()
    starts = [index for index in (text.find("{"), text.find("[")) if index >= 0]
    if not starts:
        raise json.JSONDecodeError("No JSON value found", text, 0)
    value, _ = json.JSONDecoder().raw_decode(text[min(starts):])
    return value
