from collections.abc import AsyncGenerator

from app.services.path_service import PathService


class _LegacyLLMAdapter:
    def __init__(self, llm):
        self.llm = llm

    async def complete(self, prompt):
        return self.llm.chat(prompt, max_tokens=2048)


class PathAgent:
    """Streaming adapter used by the chat orchestrator."""

    def __init__(self, llm, user_id, db, rag=None, profile=None):
        if rag is None:
            from app.api.knowledge import get_knowledge_service
            rag = get_knowledge_service()
        if profile is None:
            from app.services.profile_service import ProfileService
            profile = ProfileService(db)
        self.user_id = user_id
        llm_service = llm if callable(getattr(llm, "complete", None)) else _LegacyLLMAdapter(llm)
        self.service = PathService(db, llm_service, rag, profile)

    async def plan(self, message: str, course: str = "general") -> AsyncGenerator[dict, None]:
        yield {"type": "status", "content": "正在读取你的画像和学习资料..."}
        path = await self.service.generate(self.user_id, message, course)
        yield {"type": "path_created", "data": {"path_id": path.id, "steps": len(path.path_data)}}
