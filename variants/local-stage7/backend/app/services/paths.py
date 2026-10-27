from __future__ import annotations

import asyncio
from typing import Any

from app.agents.shared import evidence_text, parse_json_object


class PathService:
    def __init__(self, knowledge, profiles, llm_factory, store) -> None:
        self.knowledge = knowledge
        self.profiles = profiles
        self.llm_factory = llm_factory
        self.store = store

    async def generate(self, user_id: int, goal: str) -> dict[str, Any]:
        retrieval = await asyncio.to_thread(self.knowledge.retrieve, goal)
        profile = await asyncio.to_thread(self.profiles.get, user_id)
        return await self.generate_from_context(user_id, goal, profile, retrieval)

    async def generate_from_context(
        self, user_id: int, goal: str, profile: dict[str, str], retrieval
    ) -> dict[str, Any]:
        prompt = (
            "[PATH]\n只输出 JSON 对象，字段为 title、goal、steps；steps 至少一个，"
            "每步包含 title 和 description。"
            f"\n学习目标：{goal}\n学生画像：{profile}"
            f"\n知识证据：{evidence_text(retrieval)}"
        )
        raw = await asyncio.to_thread(self.llm_factory("high").chat, prompt)
        plan = parse_json_object(raw)
        self._validate_plan(plan)
        return await asyncio.to_thread(self.store.save, user_id, plan)

    @staticmethod
    def _validate_plan(plan: dict[str, Any]) -> None:
        if not all(
            isinstance(plan.get(key), str) and plan[key].strip()
            for key in ("title", "goal")
        ):
            raise ValueError("学习路径缺少 title 或 goal")
        steps = plan.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError("学习路径必须包含步骤")
        if any(
            not isinstance(step, dict)
            or not str(step.get("title", "")).strip()
            or not str(step.get("description", "")).strip()
            for step in steps
        ):
            raise ValueError("学习路径步骤格式错误")

    def get(self, user_id: int, path_id: int) -> dict[str, Any]:
        return self.store.get(user_id, path_id)

    def update_progress(
        self, user_id: int, path_id: int, step_id: int, progress: float
    ) -> dict[str, Any]:
        return self.store.update_progress(user_id, path_id, step_id, progress)
