import asyncio
import inspect
import json

from pydantic import ValidationError

from app.models import LearningResource, ResourceLink
from app.schemas.resources import CodeCaseResult, DocumentResult, MindmapResult, QuizResult, VideoScriptResult


class ResourceGenerationError(RuntimeError):
    pass


class ResourceGenerationService:
    TYPES = ("document", "mindmap", "quiz", "video_script", "code_case")
    MODELS = {"document": DocumentResult, "mindmap": MindmapResult, "quiz": QuizResult, "video_script": VideoScriptResult, "code_case": CodeCaseResult}

    def __init__(self, llm_service, rag_store, db, achievement_service=None):
        self.llm = llm_service
        self.rag = rag_store
        self.db = db
        self.achievement_service = achievement_service

    async def _call(self, function, *args, **kwargs):
        if inspect.iscoroutinefunction(function):
            return await function(*args, **kwargs)
        value = await asyncio.to_thread(function, *args, **kwargs)
        return await value if inspect.isawaitable(value) else value

    def _profile_guidance(self, profile):
        text = json.dumps(profile or {}, ensure_ascii=False)
        guidance = []
        if "基础弱" in text or "beginner" in text.lower():
            guidance.append("Use simpler language, explain prerequisites, and proceed step by step.")
        if "hands_on" in text.lower() or "实操" in text:
            guidance.append("Include more runnable code and hands-on examples.")
        return " ".join(guidance) or "Adapt depth to the learner profile."

    async def _generate_one(self, kind, user_id, topic, course, profile):
        hits = await self._call(self.rag.search, f"{topic} {kind}", user_id, course, top_k=5)
        prompt = f"RESOURCE_TYPE:{kind} Return JSON only. Topic: {topic}. Course: {course}. {self._profile_guidance(profile)} RAG: {json.dumps(hits, ensure_ascii=False)}"
        if hasattr(self.llm, "chat"):
            raw = await self._call(self.llm.chat, prompt, max_tokens=4096)
        else:
            raw = await self._call(self.llm.complete, prompt)
        data = raw if isinstance(raw, dict) else json.loads(raw)
        return kind, self.MODELS[kind].model_validate(data)

    async def generate_all(self, user, topic, course, profile):
        tasks = [asyncio.create_task(self._generate_one(kind, user.id, topic, course, profile)) for kind in self.TYPES]
        try:
            generated = await asyncio.gather(*tasks)
            resources = []
            for kind, result in generated:
                body = result.model_dump()
                content_key = {"document": "markdown", "mindmap": "mindmap", "quiz": "questions", "video_script": "scenes", "code_case": "code"}[kind]
                content = body[content_key] if isinstance(body[content_key], str) else json.dumps(body[content_key], ensure_ascii=False)
                resource = LearningResource(user_id=user.id, resource_type=kind, title=result.summary_card.title, content=content, rendered_html=f'<div class="mermaid">{content}</div>' if kind == "mindmap" else "", metadata_json={"topic": topic, "course": course, "summary_card": body["summary_card"], "tips": body["tips"], "citations": body["citations"]})
                self.db.add(resource); resources.append((resource, body))
            self.db.flush()
            document = next(resource for resource, _ in resources if resource.resource_type == "document")
            for resource, _ in resources:
                if resource is not document:
                    self.db.add(ResourceLink(user_id=user.id, source_resource_id=resource.id, target_resource_id=document.id, relation="supports", metadata_json={"topic": topic}))
            if self.achievement_service:
                self.achievement_service.evaluate(user.id, "resources_generated", {"resource_types": list(self.TYPES)}, commit=False)
            self.db.commit()
            return [{"type": "resource", "payload": {"id": resource.id, "resource_type": resource.resource_type, "title": resource.title, **body}} for resource, body in resources]
        except Exception as exc:
            for task in tasks:
                if not task.done(): task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            self.db.rollback()
            raise ResourceGenerationError(f"resource batch generation failed: {exc}") from exc
