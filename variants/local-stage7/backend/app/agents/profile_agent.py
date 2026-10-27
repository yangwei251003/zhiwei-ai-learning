from __future__ import annotations

import asyncio
import json
from typing import Any

from app.agents.shared import emit, parse_json_object
from app.agents.state import AgentState


PROFILE_DIMENSIONS = {
    "knowledge_base",
    "cognitive_style",
    "weak_points",
    "learning_goal",
    "professional_direction",
    "interest_preferences",
}


async def run_profile_agent(state: AgentState, dependencies: Any) -> dict:
    emit(
        {
            "type": "thinking",
            "agent": "profile_agent",
            "content": "正在更新六维学习画像",
        }
    )
    profile = await asyncio.to_thread(dependencies.profiles.get, state["user_id"])
    # Fast path: skip LLM for very short / non-informative messages (saves ~3s)
    msg = state["message"].strip()
    if len(msg) < 4 or not any(c.isalpha() or "\u4e00" <= c <= "\u9fff" for c in msg):
        return {"profile": profile, "profile_updates": {}}
    emit(
        {
            "type": "thinking",
            "agent": "profile_agent",
            "content": "正在分析学习情况",
        }
    )
    prompt = (
        "[PROFILE]\n"
        "从本轮对话中提取可确认的学生画像增量，只输出 JSON 对象；没有更新则输出 {}。"
        f"允许字段：{sorted(PROFILE_DIMENSIONS)}\n"
        f"当前画像：{json.dumps(profile, ensure_ascii=False)}\n"
        f"用户消息：{state['message']}"
    )
    raw = await asyncio.to_thread(dependencies.llm_factory("medium").chat, prompt)
    parsed = parse_json_object(raw)
    updates = {
        key: str(value).strip()
        for key, value in parsed.items()
        if key in PROFILE_DIMENSIONS and str(value).strip()
    }
    if updates:
        profile = await asyncio.to_thread(
            dependencies.profiles.update, state["user_id"], updates
        )
        for dimension, value in updates.items():
            emit(
                {
                    "type": "profile_update",
                    "agent": "profile_agent",
                    "payload": {"dimension": dimension, "value": value},
                }
            )
    return {"profile": profile, "profile_updates": updates}
