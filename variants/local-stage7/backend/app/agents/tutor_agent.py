from __future__ import annotations

import asyncio
import re
from typing import Any

from app.agents.shared import emit, evidence_text
from app.agents.state import AgentState
from app.core.llm import SparkAPIError


def valid_tutor_draft(content: str) -> bool:
    required = (
        "## 文字讲解",
        "诊断理解",
        "启发讲解",
        "迁移练习",
        "## 结构图解",
        "## 视频脚本",
    )
    if not all(section in content for section in required):
        return False
    diagram = re.search(r"```mermaid\s*([\s\S]*?)```", content, re.IGNORECASE)
    if not diagram or not re.match(
        r"^(?:flowchart|graph)\b", diagram.group(1).strip(), re.IGNORECASE
    ):
        return False
    if re.search(r"[<{}]", diagram.group(1)):
        return False
    return all(column in content for column in ("镜头号", "画面", "旁白", "时长"))


async def run_tutor_agent(state: AgentState, dependencies: Any) -> dict:
    emit({"type": "thinking", "agent": "tutor_agent", "content": "正在组织三段式辅导"})
    prompt = (
        "[TUTOR]\n采用“诊断理解—启发讲解—迁移练习”三段式教学。"
        "输出必须同时支持三种呈现，并使用以下 Markdown 结构："
        "\n## 文字讲解\n包含诊断理解、启发讲解、迁移练习三个小节；"
        "\n## 结构图解\n必须包含一个从 ```mermaid 开始、以 ``` 结束的严格 Mermaid flowchart；"
        '节点文字只能使用短句并放在双引号方括号中，例如 A["计算梯度"]；'
        "图内禁止 HTML、花括号、公式、下标和 LaTeX，公式必须写在图外的文字讲解中；"
        "\n## 视频脚本\n必须包含镜头号、画面、旁白、时长四列的 Markdown 表格。"
        "不得省略任一部分，不得使用假链接或假播放器。"
        f"\n问题：{state['message']}\n画像：{state.get('profile', {})}"
        f"\n知识证据：{evidence_text(state['retrieval'])}"
    )
    # Stream tokens so the user sees progress instead of a 30s silence.
    # If the streamed draft is valid, return it directly so response_agent can skip a full re-generation.
    chunks: list[str] = []
    async for token in dependencies.llm_factory("medium").chat_stream(prompt):
        chunks.append(token)
        emit(
            {
                "type": "token",
                "agent": "tutor_agent",
                "content": token,
            }
        )
    draft = "".join(chunks)
    if valid_tutor_draft(draft):
        return {"draft_response": draft, "final_response": draft}
    # Retry once with stricter instructions if the format is invalid
    retry_prompt = prompt + (
        "\n上一次输出未通过 Tutor 格式校验。请完整重写三种呈现，"
        "Mermaid 仅使用简单 flowchart、双引号短节点文字和 --> 连线。"
    )
    chunks = []
    async for token in dependencies.llm_factory("medium").chat_stream(retry_prompt):
        chunks.append(token)
        emit({"type": "token", "agent": "tutor_agent", "content": token})
    draft = "".join(chunks)
    if valid_tutor_draft(draft):
        return {"draft_response": draft, "final_response": draft}
    raise SparkAPIError("Spark returned an invalid Tutor presentation format")
