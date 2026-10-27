from __future__ import annotations

import asyncio
import time

import pytest

from app.agents.orchestrator import AgentDependencies, build_agent_graph
from app.agents.resource_agent import run_resource_agent
from app.agents.status import AgentStatusRegistry
from app.agents.tutor_agent import run_tutor_agent
from app.services.knowledge import KnowledgeHit, RetrievalResult


class FakeKnowledge:
    def __init__(self, is_hit: bool = True) -> None:
        self.is_hit = is_hit
        self.queries: list[str] = []

    def retrieve(self, query: str, limit: int = 5) -> RetrievalResult:
        self.queries.append(query)
        hits = (
            [KnowledgeHit(1, 1, "可信课程内容", "course.txt", 0.9)]
            if self.is_hit
            else []
        )
        return RetrievalResult(is_hit=self.is_hit, hits=hits)


class FakeProfiles:
    def __init__(self) -> None:
        self.profile = {"learning_goal": "掌握 Python"}
        self.updates: list[dict[str, str]] = []

    def get(self, user_id: int) -> dict[str, str]:
        return dict(self.profile)

    def update(self, user_id: int, updates: dict[str, str]) -> dict[str, str]:
        self.updates.append(updates)
        self.profile.update(updates)
        return dict(self.profile)


class FakeLLM:
    def __init__(self, level: str, owner: "FakeLLMs") -> None:
        self.level = level
        self.owner = owner

    def chat(self, prompt: str, max_tokens: int = 2048) -> str:
        self.owner.calls.append((self.level, prompt))
        if prompt.startswith("[PROFILE]"):
            return '{"professional_direction":"人工智能"}'
        if prompt.startswith("[INTENT]"):
            return self.owner.intent
        if prompt.startswith("[RESOURCE:"):
            time.sleep(0.06)
            resource_type = prompt.split("]", 1)[0][10:]
            if resource_type == "mindmap":
                return "```mermaid\nflowchart TD\nA[概念] --> B[应用]\n```"
            if resource_type == "code":
                return "```python\nprint('generated code')\n```"
            return f"generated {resource_type}"
        if prompt.startswith("[PATH]"):
            return "个性化路径草案"
        if prompt.startswith("[TUTOR]"):
            return (
                "## 文字讲解\n### 诊断理解\n确认卡点。\n"
                "### 启发讲解\n分步理解。\n### 迁移练习\n完成练习。\n"
                "## 结构图解\n```mermaid\nflowchart TD\n"
                'A["诊断"] --> B["讲解"]\nB --> C["练习"]\n```\n'
                "## 视频脚本\n|镜头号|画面|旁白|时长|\n"
                "|---|---|---|---|\n|1|概念图|先诊断|5秒|"
            )
        raise AssertionError(f"unexpected chat prompt: {prompt}")

    async def chat_stream(self, prompt: str, max_tokens: int = 2048):
        self.owner.stream_calls.append((self.level, prompt))
        for token in ["回答", "完成"]:
            await asyncio.sleep(0)
            yield token


class FakeLLMs:
    def __init__(self, intent: str) -> None:
        self.intent = intent
        self.calls: list[tuple[str, str]] = []
        self.stream_calls: list[tuple[str, str]] = []

    def __call__(self, level: str) -> FakeLLM:
        return FakeLLM(level, self)


def dependencies(intent: str, *, is_hit: bool = True):
    knowledge = FakeKnowledge(is_hit)
    profiles = FakeProfiles()
    llms = FakeLLMs(intent)
    return AgentDependencies(knowledge, profiles, llms), knowledge, profiles, llms


@pytest.mark.asyncio
async def test_state_graph_retrieves_updates_profile_routes_and_streams() -> None:
    deps, knowledge, profiles, llms = dependencies("tutor")
    graph = build_agent_graph(deps)

    result = await graph.ainvoke({"user_id": 7, "message": "请辅导我学递归"})

    assert knowledge.queries[0] == "请辅导我学递归"
    assert profiles.updates == [{"professional_direction": "人工智能"}]
    assert result["intent"] == "tutor"
    assert result["final_response"] == "回答完成"
    assert llms.calls[0][0] == "high"
    assert any(
        level == "low" and prompt.startswith("[INTENT]") for level, prompt in llms.calls
    )
    assert llms.stream_calls[0][0] == "high"
    assert set(graph.get_graph().nodes) >= {
        "retrieve_context",
        "profile_agent",
        "intent_classifier",
        "tutor_agent",
        "response_agent",
    }


@pytest.mark.asyncio
async def test_graph_emits_typed_custom_events_from_nodes() -> None:
    deps, _, _, _ = dependencies("general")
    graph = build_agent_graph(deps)

    events = [
        event
        async for event in graph.astream(
            {"user_id": 7, "message": "你好"},
            stream_mode=["updates", "custom"],
            version="v2",
        )
    ]
    custom = [event["data"] for event in events if event["type"] == "custom"]

    assert any(event["type"] == "thinking" for event in custom)
    assert any(event["type"] == "profile_update" for event in custom)
    assert [event["content"] for event in custom if event["type"] == "token"] == [
        "回答",
        "完成",
    ]


@pytest.mark.asyncio
async def test_five_resources_run_concurrently_with_independent_retrieval() -> None:
    deps, knowledge, _, llms = dependencies("resource")
    saved: list[tuple[int, int | None, list[dict]]] = []

    class Resources:
        def save_many(self, user_id, conversation_id, resources):
            saved.append((user_id, conversation_id, resources))
            return [
                dict(resource, id=index) for index, resource in enumerate(resources, 1)
            ]

    deps = AgentDependencies(
        deps.knowledge, deps.profiles, deps.llm_factory, resources=Resources()
    )
    graph = build_agent_graph(deps)

    started = time.perf_counter()
    result = await graph.ainvoke(
        {"user_id": 7, "conversation_id": 12, "message": "生成 Python 资源"}
    )
    elapsed = time.perf_counter() - started

    assert elapsed < 0.22
    assert len(result["resources"]) == 5
    assert {resource["type"] for resource in result["resources"]} == {
        "document",
        "mindmap",
        "quiz",
        "video",
        "code",
    }
    assert len(knowledge.queries) == 6
    resource_levels = {
        prompt.split("]", 1)[0][10:]: level
        for level, prompt in llms.calls
        if prompt.startswith("[RESOURCE:")
    }
    assert resource_levels["code"] == "high"
    assert set(resource_levels.values()) == {"high", "medium"}
    assert [resource["id"] for resource in result["resources"]] == [1, 2, 3, 4, 5]
    assert saved[0][:2] == (7, 12)


@pytest.mark.asyncio
async def test_resource_agent_retries_invalid_mindmap_before_persisting() -> None:
    knowledge = FakeKnowledge()
    prompts: list[str] = []
    mindmap_attempts = 0
    saved: list[list[dict]] = []

    class LLM:
        def chat(self, prompt: str, max_tokens: int = 2048) -> str:
            nonlocal mindmap_attempts
            prompts.append(prompt)
            resource_type = prompt.split("]", 1)[0][10:]
            if resource_type == "mindmap":
                mindmap_attempts += 1
                if mindmap_attempts == 1:
                    return "这里是思维导图说明，请点击查看。"
                return "```mermaid\nflowchart TD\nA[二叉树] --> B[前序遍历]\n```"
            if resource_type == "code":
                return "```python\nprint('tree')\n```"
            return f"真实 {resource_type} 内容"

    class Resources:
        def save_many(self, user_id, conversation_id, resources):
            saved.append(resources)
            return resources

    dependencies = AgentDependencies(
        knowledge,
        FakeProfiles(),
        lambda level: LLM(),
        resources=Resources(),
    )

    result = await run_resource_agent(
        {
            "user_id": 7,
            "conversation_id": 12,
            "message": "生成二叉树五类资源",
            "profile": {},
        },
        dependencies,
    )

    mindmap = next(item for item in result["resources"] if item["type"] == "mindmap")
    assert mindmap_attempts == 2
    assert mindmap["content"].startswith("```mermaid")
    assert saved[0] == result["resources"]
    assert any("只输出一个完整的 Mermaid 围栏代码块" in prompt for prompt in prompts)


@pytest.mark.asyncio
async def test_tutor_agent_retries_mermaid_with_unsafe_formula_syntax() -> None:
    prompts: list[str] = []

    class LLM:
        def chat(self, prompt: str, max_tokens: int = 2048) -> str:
            prompts.append(prompt)
            if len(prompts) == 1:
                return (
                    "## 文字讲解\n诊断理解\n"
                    "## 结构图解\n```mermaid\nflowchart TD\n"
                    "A[更新规则：<br>x_{n+1}=x_n-η] --> B[收敛]\n```\n"
                    "## 视频脚本\n|镜头号|画面|旁白|时长|\n|---|---|---|---|"
                )
            return (
                "## 文字讲解\n### 诊断理解\n先确认方向。\n"
                "### 启发讲解\n负梯度下降最快。\n### 迁移练习\n尝试一步更新。\n"
                "## 结构图解\n```mermaid\nflowchart TD\n"
                'A["观察当前位置"] --> B["计算梯度"]\n'
                'B --> C["沿反方向更新"]\n```\n'
                "## 视频脚本\n|镜头号|画面|旁白|时长|\n"
                "|---|---|---|---|\n|1|曲面|观察下降方向|5秒|"
            )

    dependencies = AgentDependencies(
        FakeKnowledge(),
        FakeProfiles(),
        lambda level: LLM(),
    )
    retrieval = FakeKnowledge().retrieve("梯度下降")

    result = await run_tutor_agent(
        {
            "user_id": 7,
            "message": "为什么沿负梯度更新",
            "profile": {},
            "retrieval": retrieval,
        },
        dependencies,
    )

    assert len(prompts) == 2
    assert "<br>" not in result["draft_response"]
    assert "计算梯度" in result["draft_response"]
    assert "节点文字只能使用短句" in prompts[0]


@pytest.mark.asyncio
async def test_weak_retrieval_forces_uncertainty_instruction() -> None:
    deps, _, _, llms = dependencies("general", is_hit=False)

    await build_agent_graph(deps).ainvoke({"user_id": 7, "message": "未知知识"})

    assert "我不确定" in llms.stream_calls[0][1]


@pytest.mark.asyncio
async def test_path_branch_persists_structured_plan_through_path_service() -> None:
    deps, _, _, _ = dependencies("path")
    calls: list[tuple] = []

    class Paths:
        async def generate_from_context(self, user_id, goal, profile, retrieval):
            calls.append((user_id, goal, profile, retrieval.is_hit))
            return {"id": 8, "title": "路线", "goal": goal, "steps": []}

    deps = AgentDependencies(
        deps.knowledge,
        deps.profiles,
        deps.llm_factory,
        path_service=Paths(),
    )

    result = await build_agent_graph(deps).ainvoke(
        {"user_id": 7, "message": "规划学习路线"}
    )

    assert result["path"]["id"] == 8
    assert calls[0][:2] == (7, "规划学习路线")


@pytest.mark.asyncio
async def test_agent_status_registry_observes_real_graph_nodes() -> None:
    deps, _, _, _ = dependencies("tutor")
    registry = AgentStatusRegistry()
    deps = AgentDependencies(
        deps.knowledge, deps.profiles, deps.llm_factory, status=registry
    )

    await build_agent_graph(deps).ainvoke({"user_id": 7, "message": "辅导我"})

    statuses = {item["name"]: item for item in registry.snapshot()}
    assert statuses["retriever"]["run_count"] == 1
    assert statuses["tutor_agent"]["run_count"] == 1
    assert statuses["resource_agent"]["run_count"] == 0
    assert all(item["status"] == "idle" for item in statuses.values())


@pytest.mark.asyncio
async def test_disabled_specialist_routes_to_general_agent() -> None:
    deps, _, _, _ = dependencies("tutor")
    registry = AgentStatusRegistry()
    registry.set_enabled("tutor_agent", False)
    deps = AgentDependencies(
        deps.knowledge, deps.profiles, deps.llm_factory, status=registry
    )

    result = await build_agent_graph(deps).ainvoke({"user_id": 7, "message": "辅导我"})

    assert result["intent"] == "general"
    statuses = {item["name"]: item for item in registry.snapshot()}
    assert statuses["tutor_agent"]["run_count"] == 0
    assert statuses["general_agent"]["run_count"] == 1


@pytest.mark.asyncio
async def test_invalid_verbose_spark_intent_falls_back_to_message_semantics() -> None:
    deps, _, _, _ = dependencies(
        "[intent] resource: 二叉树遍历 path: 解释二叉树遍历 tutor: 薄弱点 general: 无"
    )

    result = await build_agent_graph(deps).ainvoke(
        {"user_id": 7, "message": "请解释二叉树遍历，并说明我的薄弱点"}
    )

    assert result["intent"] == "tutor"
    assert result["final_response"] == "回答完成"


@pytest.mark.asyncio
async def test_tutor_prompts_require_and_preserve_all_three_presentations() -> None:
    deps, _, _, llms = dependencies("tutor")

    await build_agent_graph(deps).ainvoke(
        {"user_id": 7, "message": "为什么梯度下降沿负梯度更新"}
    )

    tutor_prompt = next(
        prompt for _, prompt in llms.calls if prompt.startswith("[TUTOR]")
    )
    response_prompt = llms.stream_calls[0][1]
    assert "诊断理解" in tutor_prompt
    assert "```mermaid" in tutor_prompt
    assert "视频脚本" in tutor_prompt
    assert "不得删除或改写 Mermaid" in response_prompt
    assert "视频脚本" in response_prompt


@pytest.mark.asyncio
async def test_explicit_resource_command_overrides_a_valid_but_wrong_general_intent() -> (
    None
):
    deps, _, _, _ = dependencies("general")

    result = await build_agent_graph(deps).ainvoke(
        {"user_id": 7, "message": "请生成五类学习资源和可运行 Python 代码"}
    )

    assert result["intent"] == "resource"
    assert len(result["resources"]) == 5
