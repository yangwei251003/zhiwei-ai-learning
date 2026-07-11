"""
辅导 Agent - 多模态答疑解惑
"""

import logging
import json
from typing import AsyncGenerator
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TutorAgent:
    """智能辅导 Agent：检索知识库 + 生成多模态解答"""

    def __init__(self, llm, user_id: int, db: Session):
        self.llm = llm
        self.user_id = user_id
        self.db = db

    async def run(self, state) -> AsyncGenerator[dict, None]:
        question, course = state["message"], state["course"]
        context = {
            "history": state.get("history", []),
            "profile": state.get("profile", {}),
            "rag_chunks": state.get("rag_chunks", []),
        }
        prompt = f"""你是一位耐心的 AI 助教，请回答学生的问题。
课程：{course}
对话与学习上下文：{json.dumps(context, ensure_ascii=False)}
学生问题：{question}
要求：先直接回答，再分点解释；不确定时明确说明。"""
        async for chunk in self.llm.stream(prompt):
            yield {"type": "token", "payload": {"content": chunk}}

    async def answer(self, question: str, course: str) -> AsyncGenerator[dict, None]:
        """解答学生问题"""
        yield {"type": "status", "content": "正在检索相关知识..."}

        # 1. 检索相关知识（此处简化，后续接 Chroma 向量检索）
        knowledge_context = f"课程：{course}\n学生问题：{question}"

        # 2. 生成解答
        yield {"type": "status", "content": "正在生成解答..."}

        prompt = f"""你是一位耐心的 AI 助教，请回答学生的问题。

{knowledge_context}

要求：
1. 先给出简洁直接的回答（2-3 句）
2. 然后详细解释原理（分点列出）
3. 如果适合作图说明，输出 Mermaid 图
4. 如果有练习需求，推荐相关练习题
5. 如果不知道，明确说"我不确定"

学生问题: {question}"""
        if hasattr(self.llm, "complete"):
            response = await self.llm.complete(prompt)
        else:
            response = self.llm.chat(prompt, max_tokens=2048)

        yield {"type": "text", "content": response}

        # 3. 检查是否需要生成图解
        yield {"type": "tutor_complete", "data": {"question": question}}
