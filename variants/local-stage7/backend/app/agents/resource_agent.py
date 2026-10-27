from __future__ import annotations

import asyncio
import re
from typing import Any

from app.agents.shared import emit, evidence_text
from app.agents.state import AgentState
from app.core.llm import SparkAPIError


RESOURCE_SPECS = {
    "document": ("讲解文档，结构化 Markdown，含目录、小节和代码示例", "medium"),
    "mindmap": (
        "只输出一个完整的 Mermaid 围栏代码块（从 ```mermaid 开始、以 ``` 结束），"
        "围栏内必须以 flowchart、graph 或 mindmap 开头，围栏外不要写说明",
        "medium",
    ),
    "quiz": ("至少五道练习题，含答案、解析和难度标签", "medium"),
    "video": ("视频分镜表，含镜头号、画面、旁白和时长", "medium"),
    "code": (
        "必须包含一个完整的 ```python 围栏代码块，代码可直接运行，含注释和预期输出，"
        "不得使用省略号或占位符代替实现",
        "high",
    ),
}


def valid_resource_content(resource_type: str, content: str) -> bool:
    if resource_type == "mindmap":
        match = re.search(r"```mermaid\s*([\s\S]*?)```", content, re.IGNORECASE)
        return bool(
            match
            and re.match(
                r"^(?:flowchart|graph|mindmap)\b",
                match.group(1).strip(),
                re.IGNORECASE,
            )
        )
    if resource_type == "code":
        match = re.search(r"```(?:python|py)\s*([\s\S]*?)```", content, re.IGNORECASE)
        return bool(match and match.group(1).strip())
    return bool(content.strip())


async def run_resource_agent(state: AgentState, dependencies: Any) -> dict:
    emit(
        {
            "type": "thinking",
            "agent": "resource_agent",
            "content": "正在并行生成五类资源",
        }
    )

    async def generate(resource_type: str, requirement: str, level: str) -> dict:
        retrieval = await asyncio.to_thread(
            dependencies.knowledge.retrieve,
            f"{state['message']} {resource_type}",
        )
        prompt = (
            f"[RESOURCE:{resource_type}]\n"
            f"任务：{requirement}\n用户需求：{state['message']}\n"
            f"学生画像：{state.get('profile', {})}\n知识证据：{evidence_text(retrieval)}"
        )
        content = ""
        for attempt in range(2):
            attempt_prompt = prompt
            if attempt:
                attempt_prompt += (
                    "\n上一次输出未通过格式校验。必须严格按任务格式重新生成，"
                    "不要解释格式要求。"
                )
            content = await asyncio.to_thread(
                dependencies.llm_factory(level).chat,
                attempt_prompt,
            )
            if valid_resource_content(resource_type, content):
                break
        else:
            raise SparkAPIError(
                f"Spark returned invalid {resource_type} resource format"
            )
        resource = {
            "type": resource_type,
            "title": f"{state['message']} · {resource_type}",
            "content": content,
        }
        return resource

    resources = await asyncio.gather(
        *(
            generate(resource_type, requirement, level)
            for resource_type, (requirement, level) in RESOURCE_SPECS.items()
        )
    )
    if dependencies.resources is not None:
        resources = await asyncio.to_thread(
            dependencies.resources.save_many,
            state["user_id"],
            state.get("conversation_id"),
            resources,
        )
    for resource in resources:
        emit(
            {
                "type": "resource",
                "agent": "resource_agent",
                "payload": resource,
            }
        )
    return {
        "resources": resources,
        "draft_response": "五类学习资源已经生成，可在资源库中继续查看。",
    }
