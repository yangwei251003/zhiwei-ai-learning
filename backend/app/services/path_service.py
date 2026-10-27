import json
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import LearningPath, LearningResource
from app.llm.json_output import extract_json_value
from app.schemas.path import PathPlan


class PathNotFound(LookupError):
    pass


class PathValidationError(ValueError):
    pass


class PathService:
    def __init__(self, db: Session, llm: Any, rag: Any, profile: Any):
        self.db, self.llm, self.rag, self.profile = db, llm, rag, profile

    @staticmethod
    def _dump(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, dict):
            return value
        return {key: val for key, val in vars(value).items() if not key.startswith("_")}

    async def generate(self, user_id: int, message: str, course: str) -> LearningPath:
        profile = self.profile.current(user_id)
        resources = self.db.scalars(
            select(LearningResource).where(LearningResource.user_id == user_id)
        ).all()
        rag_hits = self.rag.search(message, user_id, course, top_k=5)
        context = {
            "student_profile": self._dump(profile),
            "existing_resources": [
                {"id": item.id, "title": item.title, "resource_type": item.resource_type}
                for item in resources
            ],
            "rag_top_5": rag_hits,
            "course": course,
            "request": message,
        }
        prompt = (
            "Generate a personalized learning path from the supplied context. Return JSON only, "
            "matching {steps:[{step,topic,description,estimated_minutes,resource_types_needed,status}]}. "
            "There must be 5-8 sequential steps starting at 1; estimated_minutes must be positive; "
            "resource_types_needed values must be document, quiz, mindmap, video_script, or code_case; "
            "every status must be pending. Context:\n" + json.dumps(context, ensure_ascii=False, default=str)
        )
        try:
            raw = await self.llm.complete(prompt)
            plan = PathPlan.model_validate(extract_json_value(raw))
        except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise PathValidationError("LLM returned an invalid learning path") from exc
        if [step.step for step in plan.steps] != list(range(1, len(plan.steps) + 1)):
            raise PathValidationError("learning path steps must be sequential")
        if any(step.status != "pending" for step in plan.steps):
            raise PathValidationError("new learning path steps must be pending")

        try:
            self.db.execute(
                update(LearningPath)
                .where(LearningPath.user_id == user_id, LearningPath.is_active == 1)
                .values(is_active=0)
            )
            path = LearningPath(
                user_id=user_id,
                path_data=[step.model_dump(mode="json") for step in plan.steps],
                current_step=0,
                is_active=1,
            )
            self.db.add(path)
            self.db.commit()
            self.db.refresh(path)
            return path
        except Exception:
            self.db.rollback()
            raise

    def current(self, user_id: int) -> LearningPath:
        path = self.db.scalar(
            select(LearningPath).where(
                LearningPath.user_id == user_id, LearningPath.is_active == 1
            ).order_by(LearningPath.created_at.desc(), LearningPath.id.desc())
        )
        if path is None:
            raise PathNotFound("active learning path not found")
        return path

    def update_progress(self, user_id: int, path_id: int, step: int, status: str) -> LearningPath:
        rank = {"pending": 0, "in_progress": 1, "completed": 2}
        if status not in rank:
            raise PathValidationError("invalid status")
        for _ in range(3):
            path = self.db.scalar(
                select(LearningPath).where(
                    LearningPath.id == path_id, LearningPath.user_id == user_id
                )
            )
            if path is None:
                raise PathNotFound("learning path not found")
            original = path.path_data or []
            steps = [dict(item) for item in original]
            if step < 1 or step > len(steps):
                raise PathValidationError("step is outside the learning path")
            old = steps[step - 1].get("status", "pending")
            if rank[status] >= rank.get(old, 0):
                steps[step - 1]["status"] = status
            contiguous = 0
            for item in steps:
                if item.get("status") != "completed":
                    break
                contiguous += 1
            result = self.db.execute(
                update(LearningPath).where(
                    LearningPath.id == path_id,
                    LearningPath.user_id == user_id,
                    LearningPath.path_data == original,
                ).values(
                    path_data=steps,
                    current_step=max(path.current_step or 0, contiguous),
                )
            )
            if result.rowcount == 1:
                self.db.commit()
                self.db.expire_all()
                return self.db.get(LearningPath, path_id)
            self.db.rollback()
            self.db.expire_all()
        raise PathValidationError("learning path was updated concurrently; retry")
