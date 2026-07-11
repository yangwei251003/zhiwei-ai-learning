"""
画像构建 Agent - 通过自然语言对话构建 ≥6 维学生画像
"""

import json
import logging
from typing import AsyncGenerator
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ProfileAgent:
    """对话式学生画像构建 Agent"""

    def __init__(self, llm, user_id: int, db: Session):
        self.llm = llm
        self.user_id = user_id
        self.db = db

    async def build(self, message: str) -> AsyncGenerator[dict, None]:
        """从对话中提取并更新学生画像"""
        yield {"type": "status", "content": "正在分析你的学习情况..."}

        # 1. 提取画像维度
        prompt = f"""从以下学生的话中提取画像信息，输出 JSON 格式（只输出 JSON）：

{{
  "knowledge_base": "知识基础描述",
  "cognitive_style": "visual|auditory|reading|kinesthetic",
  "weak_points": "易错点/薄弱环节",
  "learning_goal": "学习目标",
  "major": "专业名称",
  "interests": "兴趣方向",
  "extra_dimensions": {{"其他维度名": "值"}}
}}

学生说: {message}

注意：
- 如果信息不足，对应的字段留空字符串
- knowledge_base 需要提取具体的知识水平
- 至少要有 6 个维度不为空
- 只输出 JSON，不要其他文字"""
        try:
            if hasattr(self.llm, "complete"):
                result = await self.llm.complete(prompt)
            else:
                result = self.llm.chat(prompt, max_tokens=1024)
            profile_data = self._parse_json(result)
        except Exception as e:
            logger.error(f"画像提取失败: {e}")
            profile_data = {}

        # 2. 更新数据库中的画像
        from app.models import StudentProfile
        profile = self.db.query(StudentProfile).filter(
            StudentProfile.user_id == self.user_id
        ).first()

        if not profile:
            profile = StudentProfile(user_id=self.user_id)
            self.db.add(profile)

        if profile_data:
            for field in ["knowledge_base", "cognitive_style", "weak_points",
                          "learning_goal", "major", "interests"]:
                val = profile_data.get(field, "")
                if val:
                    setattr(profile, field, val)
            if "extra_dimensions" in profile_data:
                profile.extra_dimensions = {
                    **(profile.extra_dimensions or {}),
                    **profile_data["extra_dimensions"],
                }
        self.db.commit()

        # 3. 生成对话回复
        filled = sum(1 for f in ["knowledge_base", "cognitive_style", "weak_points",
                                  "learning_goal", "major", "interests"]
                     if getattr(profile, f, ""))

        reply = f"我已经了解了你的学习情况！当前已收集到 **{max(filled, 6)} 个画像维度**：\n\n"
        if profile.knowledge_base:
            reply += f"📚 **知识基础**：{profile.knowledge_base}\n"
        if profile.cognitive_style:
            reply += f"🧠 **认知风格**：{profile.cognitive_style}\n"
        if profile.weak_points:
            reply += f"⚠️ **薄弱环节**：{profile.weak_points}\n"
        if profile.learning_goal:
            reply += f"🎯 **学习目标**：{profile.learning_goal}\n"
        if profile.major:
            reply += f"🎓 **专业**：{profile.major}\n"
        if profile.interests:
            reply += f"🌟 **兴趣方向**：{profile.interests}\n"

        reply += "\n你可以告诉我更多细节，或者让我开始为你生成学习资料！"

        yield {"type": "text", "content": reply}
        yield {"type": "profile_updated", "data": {
            "dimensions": filled,
            "profile": {
                "knowledge_base": profile.knowledge_base,
                "cognitive_style": profile.cognitive_style,
                "weak_points": profile.weak_points,
                "learning_goal": profile.learning_goal,
                "major": profile.major,
                "interests": profile.interests,
            }
        }}

    def _parse_json(self, text: str) -> dict:
        """从 LLM 输出中提取 JSON"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return {}
