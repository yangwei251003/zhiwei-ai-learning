from typing import Any, AsyncGenerator
import asyncio

from app.agents.nodes import normalize_event

from app.agents.graph import AgentDependencies, build_agent_graph
from app.llm.service import LLMService


class _LLMServiceWithStatus(LLMService):
    def is_connected(self):
        client = self._client
        if hasattr(client, "configured"):
            return bool(client.configured)
        return all(bool(getattr(client, name, "").strip()) for name in ("app_id", "api_key", "api_secret"))


class _StreamingAgentAdapter:
    def __init__(self, agent: Any, method: str, sink=None):
        self.agent = agent
        self.method = method
        self.sink = sink

    async def run(self, state):
        if hasattr(self.agent, "run"):
            source = self.agent.run(state)
        else:
            function = getattr(self.agent, self.method)
            args = (state["message"], state["course"]) if self.method in {"generate", "answer", "plan"} else (state["message"],)
            source = function(*args)
        items = []
        async for item in source:
            items.append(item)
            if self.sink:
                await self.sink(normalize_event(item))
        return items


async def _load_database_memory(db, state):
    from app.models import Conversation, StudentProfile

    rows = (db.query(Conversation).filter(Conversation.user_id == state["user_id"])
            .order_by(Conversation.created_at.desc()).limit(12).all())
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == state["user_id"]).first()
    profile_data = {} if profile is None else {
        name: getattr(profile, name) for name in (
            "knowledge_base", "cognitive_style", "weak_points", "learning_goal",
            "major", "interests", "extra_dimensions",
        )
    }
    return {
        "history": [{"role": row.role, "content": row.content} for row in reversed(rows)],
        "profile": profile_data,
    }


class AgentOrchestrator:
    """Compatibility facade over the compiled LangGraph workflow."""

    def __init__(self, user_id: int, db, course: str = "人工智能导论", dependencies=None):
        self.user_id = user_id
        self.db = db
        self.course = course
        self._event_queue = None
        self.llm = dependencies.llm if dependencies else _LLMServiceWithStatus()
        if dependencies is None:
            dependencies = self._default_dependencies()
        self.graph = build_agent_graph(dependencies)

    def _default_dependencies(self):
        from app.agents.path_agent import PathAgent
        from app.agents.profile_agent import ProfileAgent
        from app.agents.resource_agent import ResourceAgent
        from app.agents.tutor_agent import TutorAgent

        async def memory_loader(state):
            return await _load_database_memory(self.db, state)

        return AgentDependencies(
            llm=self.llm,
            memory_loader=memory_loader,
            profile_agent=_StreamingAgentAdapter(ProfileAgent(self.llm, self.user_id, self.db), "build", self._emit),
            resource_agent=_StreamingAgentAdapter(ResourceAgent(self.llm, self.user_id, self.db), "generate", self._emit),
            path_agent=_StreamingAgentAdapter(PathAgent(self.llm, self.user_id, self.db), "plan", self._emit),
            tutor_agent=_StreamingAgentAdapter(TutorAgent(self.llm, self.user_id, self.db), "answer", self._emit),
        )

    async def _emit(self, item):
        if self._event_queue is not None:
            await self._event_queue.put(item)

    def _initial_state(self, message, conversation_id=None, rag_chunks=None):
        return {
            "user_id": self.user_id, "conversation_id": conversation_id, "message": message,
            "course": self.course, "events": [], "errors": [], "resources": [],
            "rag_chunks": rag_chunks or [],
        }

    async def process_message(self, message: str, conversation_id=None, rag_chunks=None) -> AsyncGenerator[dict, None]:
        self._event_queue = asyncio.Queue()
        async def run_graph():
            async for _ in self.graph.astream(
                self._initial_state(message, conversation_id, rag_chunks), stream_mode="updates"
            ):
                pass

        task = asyncio.create_task(run_graph())
        try:
            while not task.done() or not self._event_queue.empty():
                get_event = asyncio.create_task(self._event_queue.get())
                done, _ = await asyncio.wait({task, get_event}, return_when=asyncio.FIRST_COMPLETED)
                if get_event in done:
                    yield get_event.result()
                else:
                    get_event.cancel()
                    await asyncio.gather(get_event, return_exceptions=True)
            await task
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            self._event_queue = None

    async def process_message_sync(self, message: str) -> dict:
        result = await self.graph.ainvoke(self._initial_state(message))
        return {"reply": result.get("response_text", ""), "resources": result.get("resources", [])}
