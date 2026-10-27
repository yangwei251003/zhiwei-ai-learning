import asyncio
import json
from datetime import date
from sqlalchemy.exc import IntegrityError

from app.models import ChallengeSubmission, DailyChallenge, PointTransaction

class ChallengeNotFound(LookupError): pass
class InvalidChallenge(ValueError): pass

def normalize_answer(value): return " ".join(str(value).strip().casefold().split())

class ChallengeService:
    def __init__(self, db, llm=None, rag=None, profile=None, achievement=None, today=date.today):
        self.db, self.llm, self.rag, self.profile, self.achievement, self.today = db, llm, rag, profile, achievement, today

    def today_for(self, user_id, course):
        return self.db.query(DailyChallenge).filter_by(user_id=user_id, course=course, challenge_date=self.today()).first()

    def generate(self, user_id, course):
        current = self.today_for(user_id, course)
        if current: return current
        profile = self.profile.current(user_id) if self.profile else {}
        if not isinstance(profile, dict): profile = {k: getattr(profile, k) for k in ("weak_points", "learning_goal") if hasattr(profile, k)}
        weak = profile.get("weak_points") or []
        query = weak[0].get("name", course) if weak and isinstance(weak[0], dict) else course
        if self.rag:
            try: context = self.rag.search(query, user_id, course, top_k=5)
            except TypeError: context = self.rag.search(query, top_k=5, course=course, user_id=user_id)
        else: context = []
        if self.llm and hasattr(self.llm, "generate"):
            data = self.llm.generate(course=course, profile=profile, context=context)
        elif self.llm and hasattr(self.llm, "complete"):
            prompt = "Return strict JSON only with question_type, question, options, answer, explanation, difficulty, concept, reward. Only multiple_choice or fill_blank. " + json.dumps({"course": course, "profile": profile, "context": context}, ensure_ascii=False, default=str)
            raw = asyncio.run(self.llm.complete(prompt))
            try: data = json.loads(raw)
            except (TypeError, json.JSONDecodeError): raise InvalidChallenge("invalid challenge structure")
        else: data = None
        if not isinstance(data, dict) or data.get("question_type") not in {"multiple_choice", "fill_blank"}: raise InvalidChallenge("invalid challenge structure")
        required = {"question", "answer", "explanation", "difficulty", "concept"}
        if not required.issubset(data): raise InvalidChallenge("invalid challenge structure")
        options = data.get("options", [])
        if data["question_type"] == "multiple_choice" and (not options or data["answer"] not in options): raise InvalidChallenge("multiple choice answer must be an option")
        challenge = DailyChallenge(user_id=user_id, course=course, challenge_date=self.today(), question_type=data["question_type"], question=data["question"], options=options, answer=str(data["answer"]), explanation=data["explanation"], difficulty=float(data["difficulty"]), concept=data["concept"], reward_points=int(data.get("reward", data.get("reward_points", 0))))
        self.db.add(challenge)
        try: self.db.commit(); self.db.refresh(challenge); return challenge
        except IntegrityError:
            self.db.rollback(); return self.today_for(user_id, course)

    def _owned(self, user_id, challenge_id):
        item = self.db.query(DailyChallenge).filter_by(id=challenge_id, user_id=user_id).first()
        if not item: raise ChallengeNotFound("challenge not found")
        return item

    def submit(self, user_id, challenge_id, answer):
        challenge = self._owned(user_id, challenge_id)
        old = self.db.query(ChallengeSubmission).filter_by(challenge_id=challenge.id).first()
        if old: return {"is_correct": old.is_correct, "awarded_points": old.awarded_points, "explanation": challenge.explanation if old.is_correct else None}
        correct = normalize_answer(answer) == normalize_answer(challenge.answer)
        awarded = challenge.reward_points if correct else 0
        submission = ChallengeSubmission(challenge_id=challenge.id, answer=str(answer), is_correct=correct, awarded_points=awarded)
        self.db.add(submission)
        if correct: self.db.add(PointTransaction(user_id=user_id, delta=awarded, reason="每日挑战", reference_type="challenge", reference_id=challenge.id, idempotency_key=f"challenge:{challenge.id}"))
        try: self.db.commit()
        except IntegrityError:
            self.db.rollback(); old = self.db.query(ChallengeSubmission).filter_by(challenge_id=challenge.id).first(); return {"is_correct": old.is_correct, "awarded_points": old.awarded_points, "explanation": challenge.explanation if old.is_correct else None}
        if correct and self.achievement: self.achievement.evaluate(user_id, "challenge_completed", {"challenge_id": challenge.id})
        return {"is_correct": correct, "awarded_points": awarded, "explanation": challenge.explanation if correct else None}

    def history(self, user_id, course=None):
        query = self.db.query(DailyChallenge).filter_by(user_id=user_id)
        if course: query = query.filter_by(course=course)
        return query.order_by(DailyChallenge.challenge_date.desc()).all()
