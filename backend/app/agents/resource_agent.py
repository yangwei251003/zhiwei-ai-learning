from typing import AsyncGenerator

from app.models import StudentProfile, User
from app.services.resource_service import ResourceGenerationService


class ResourceAgent:
    """Thin streaming adapter around the atomic resource generation service."""

    def __init__(self, llm, user_id: int, db, service=None, rag_store=None):
        self.user_id = user_id
        self.db = db
        if service is None:
            if rag_store is None:
                from app.api.knowledge import get_knowledge_service
                rag_store = get_knowledge_service()
            service = ResourceGenerationService(llm, rag_store, db)
        self.service = service

    async def generate(self, message: str, course: str) -> AsyncGenerator[dict, None]:
        yield {"type": "status", "content": "正在并行生成 5 类学习资源..."}
        user = self.db.get(User, self.user_id)
        profile = self.db.query(StudentProfile).filter(StudentProfile.user_id == self.user_id).first()
        profile_data = {} if profile is None else {
            "knowledge_base": profile.knowledge_base,
            "weak_points": profile.weak_points,
            "cognitive_style": profile.cognitive_style,
        }
        cards = await self.service.generate_all(user, message.strip(), course, profile_data)
        for card in cards:
            yield {"type": "resource", "data": card["payload"]}
        yield {"type": "done", "data": {"resource_ids": [card["payload"]["id"] for card in cards], "topic": message.strip()}}
