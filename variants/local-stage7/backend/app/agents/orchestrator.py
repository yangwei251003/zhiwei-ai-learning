from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
import json
import re
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from app.agents.path_agent import run_path_agent
from app.agents.profile_agent import run_profile_agent
from app.agents.resource_agent import run_resource_agent
from app.agents.shared import emit, evidence_text
from app.agents.state import AgentState
from app.agents.tutor_agent import run_tutor_agent

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')


VALID_INTENTS = {"resource", "path", "tutor", "general"}
INTENT_KEYWORDS = {
    "resource": (
        "生成",
        "资源",
        "练习题",
        "思维导图",
        "视频脚本",
        "代码案例",
        "讲解文档",
    ),
    "path": ("路径", "计划", "规划", "安排", "复习日程", "学习顺序"),
    "tutor": ("辅导", "讲解", "解释", "为什么", "不理解", "不会", "卡住", "薄弱点"),
}


def explicit_intent(message: str) -> str | None:
    if any(verb in message for verb in ("生成", "创建", "制作")) and any(
        keyword in message
        for keyword in (
            "资源",
            "练习题",
            "思维导图",
            "视频脚本",
            "代码案例",
            "讲解文档",
        )
    ):
        return "resource"
    if any(verb in message for verb in ("规划", "制定", "安排")) and any(
        keyword in message for keyword in ("路径", "计划", "日程", "学习顺序", "复习")
    ):
        return "path"
    if any(
        keyword in message
        for keyword in ("辅导", "讲解", "解释", "不理解", "不会", "卡住")
    ):
        return "tutor"
    return None


GREETING_PATTERNS = (
    "你好", "您好", "嗨", "hi", "hello", "hey", "早上好", "晚上好", "下午好",
    "谢谢", "感谢", "不客气", "再见", "拜拜", "ok", "好的", "嗯", "哦",
)


def is_greeting_or_short(message: str) -> bool:
    """Fast path: skip LLM for greetings and very short messages."""
    msg = message.strip().lower()
    if len(msg) <= 5:
        return True
    if any(pattern in msg for pattern in GREETING_PATTERNS if len(pattern) >= 2):
        return True
    # Very short queries with no intent keywords
    if len(msg) <= 15 and explicit_intent(message) is None:
        return True
    return False


def parse_intent(content: str, message: str) -> str:
    if forced := explicit_intent(message):
        return forced
    candidate = content.strip().lower()
    if candidate in VALID_INTENTS:
        return candidate
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        candidate = "\n".join(lines[1:-1]).strip()
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict) and payload.get("intent") in VALID_INTENTS:
        return str(payload["intent"])
    mentioned = set(re.findall(r"\b(resource|path|tutor|general)\b", candidate))
    if len(mentioned) == 1:
        return mentioned.pop()
    for intent in ("resource", "path", "tutor"):
        if any(keyword in message for keyword in INTENT_KEYWORDS[intent]):
            return intent
    return "general"


@dataclass(frozen=True)
class AgentDependencies:
    knowledge: Any
    profiles: Any
    llm_factory: Callable[[str], Any]
    resources: Any | None = None
    path_service: Any | None = None
    status: Any | None = None


def build_agent_graph(dependencies: AgentDependencies):
    def observe(name: str, operation):
        async def observed(state: AgentState) -> dict:
            if dependencies.status is None:
                return await operation(state)
            if not dependencies.status.is_enabled(name):
                return {}
            async with dependencies.status.track(name):
                return await operation(state)

        return observed

    async def retrieve_context(state: AgentState) -> dict:
        emit({"type": "thinking", "agent": "retriever", "content": "正在检索知识库"})
        retrieval = await asyncio.to_thread(
            dependencies.knowledge.retrieve, state["message"]
        )
        return {"retrieval": retrieval, "retrieval_performed": True}

    async def profile_agent(state: AgentState) -> dict:
        return await run_profile_agent(state, dependencies)

    async def profile_and_intent(state: AgentState) -> dict:
        """Run profile update and intent classification in parallel - saves 2-3s."""
        # Fast path: short/greeting messages → general, skip LLM
        if is_greeting_or_short(state["message"]):
            profile_res = await run_profile_agent(state, dependencies)
            return {**profile_res, "intent": "general"}

        # Fast path: explicit keyword match → skip intent LLM
        forced = explicit_intent(state["message"])
        if forced is not None:
            profile_res = await run_profile_agent(state, dependencies)
            intent = forced
        else:
            emit({"type": "thinking", "agent": "intent_classifier", "content": "正在判断问题类型"})
            # Run LLM calls concurrently: profile + intent
            profile_task = asyncio.create_task(run_profile_agent(state, dependencies))
            intent_task = asyncio.create_task(
                asyncio.to_thread(
                    dependencies.llm_factory("low").chat,
                    (
                        "[INTENT]\n判断用户本轮主要意图。只输出一行 JSON，不要解释："
                        '{"intent":"resource|path|tutor|general"}。'
                        f"\n用户消息：{state['message']}"
                    ),
                    64,
                )
            )
            profile_res, raw_intent = await asyncio.gather(profile_task, intent_task)
            intent = parse_intent(raw_intent, state["message"])
        specialist = {
            "resource": "resource_agent",
            "path": "path_agent",
            "tutor": "tutor_agent",
        }.get(intent)
        if (
            specialist
            and dependencies.status is not None
            and not dependencies.status.is_enabled(specialist)
        ):
            intent = "general"
        return {**profile_res, "intent": intent}

    async def resource_agent(state: AgentState) -> dict:
        return await run_resource_agent(state, dependencies)

    async def path_agent(state: AgentState) -> dict:
        return await run_path_agent(state, dependencies)

    async def tutor_agent(state: AgentState) -> dict:
        return await run_tutor_agent(state, dependencies)

    async def general_agent(state: AgentState) -> dict:
        emit({"type": "thinking", "agent": "general_agent", "content": "正在组织回答"})
        return {"draft_response": ""}

    async def response_agent(state: AgentState) -> dict:
        # If a specialist agent (tutor/path) already produced a complete final_response,
        # skip the second LLM call to avoid 30+ seconds of waiting.
        if state.get("final_response"):
            return {"final_response": state["final_response"]}
        level = "high" if state["intent"] in {"path", "tutor"} else "medium"
        format_instruction = (
            "\n这是 Tutor 三种呈现结果。必须完整保留草案中的文字讲解、"
            "Mermaid 代码块和视频脚本表格；不得删除或改写 Mermaid 语法，"
            "不得省略视频脚本的镜头、画面、旁白、时长字段。"
            if state["intent"] == "tutor"
            else ""
        )
        prompt = (
            "[RESPONSE]\n基于知识证据和 Agent 草案直接回答用户，不得捏造来源。"
            f"\n用户问题：{state['message']}\n画像：{state.get('profile', {})}"
            f"\nAgent 草案：{state.get('draft_response', '')}"
            f"\n知识证据：{evidence_text(state['retrieval'])}"
            f"{format_instruction}"
        )
        tokens: list[str] = []
        async for token in dependencies.llm_factory(level).chat_stream(prompt):
            tokens.append(token)
            emit(
                {
                    "type": "token",
                    "agent": "response_agent",
                    "content": token,
                }
            )
        return {"final_response": "".join(tokens)}

    graph = StateGraph(AgentState)
    graph.add_node("retrieve_context", observe("retriever", retrieve_context))
    graph.add_node("profile_and_intent", observe("profile_agent", profile_and_intent))
    graph.add_node("resource_agent", observe("resource_agent", resource_agent))
    graph.add_node("path_agent", observe("path_agent", path_agent))
    graph.add_node("tutor_agent", observe("tutor_agent", tutor_agent))
    graph.add_node("general_agent", observe("general_agent", general_agent))
    graph.add_node("response_agent", observe("response_agent", response_agent))
    graph.add_edge(START, "retrieve_context")
    graph.add_edge("retrieve_context", "profile_and_intent")
    graph.add_conditional_edges(
        "profile_and_intent",
        lambda state: state["intent"],
        {
            "resource": "resource_agent",
            "path": "path_agent",
            "tutor": "tutor_agent",
            "general": "general_agent",
        },
    )
    for node in ("resource_agent", "path_agent", "tutor_agent", "general_agent"):
        graph.add_edge(node, "response_agent")
    graph.add_edge("response_agent", END)
    return graph.compile()
