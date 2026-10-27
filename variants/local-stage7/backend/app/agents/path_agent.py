from __future__ import annotations

import asyncio
from typing import Any

from app.agents.shared import emit, evidence_text
from app.agents.state import AgentState


async def run_path_agent(state: AgentState, dependencies: Any) -> dict:
    emit(
        {"type": "thinking", "agent": "path_agent", "content": "正在规划个性化学习路径"}
    )
    if dependencies.path_service is not None:
        path = await dependencies.path_service.generate_from_context(
            state["user_id"],
            state["message"],
            state.get("profile", {}),
            state["retrieval"],
        )
        # Make the chat reply useful: include the path title + first milestone
        first_step = ""
        try:
            steps = path.get("steps") or []
            if steps:
                first_step = f"\n\n第一步：{steps[0].get('title', '')}"
        except (AttributeError, TypeError):
            first_step = ""
        draft = (
            f"已为你生成学习路径《{path['title']}》"
            f"\n总时长：{path.get('total_hours', '?')} 小时 · "
            f"步数：{len(path.get('steps') or [])}"
            f"{first_step}\n\n请前往「学习路径」页面查看完整内容并开始学习。"
        )
        # Emit the draft as tokens so the user actually sees it in the chat UI
        for i in range(0, len(draft), 80):
            emit({"type": "token", "agent": "path_agent", "content": draft[i : i + 80]})
        return {
            "path": path,
            "draft_response": draft,
            "final_response": draft,
        }
    prompt = (
        "[PATH]\n根据画像、目标和证据设计可追踪的阶段化学习路径。"
        f"\n用户需求：{state['message']}\n画像：{state.get('profile', {})}"
        f"\n知识证据：{evidence_text(state['retrieval'])}"
    )
    # Stream so the user sees progress instead of 30s silence.
    # Returning final_response lets the orchestrator skip the second LLM pass in response_agent.
    chunks: list[str] = []
    async for token in dependencies.llm_factory("medium").chat_stream(prompt):
        chunks.append(token)
        emit({"type": "token", "agent": "path_agent", "content": token})
    draft = "".join(chunks)
    return {"draft_response": draft, "final_response": draft}
