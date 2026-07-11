from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import PointTransaction, User


class Rag:
    def __init__(self): self.calls = []
    def search(self, query, top_k=5, **kwargs): self.calls.append((query, top_k)); return ["ctx"]

class Profile:
    def current(self, user_id): return {"weak_points": [{"name": "loops"}]}

class Llm:
    def generate(self, **kwargs):
        return {"question_type": "fill_blank", "question": "2+2", "options": [], "answer": "4", "explanation": "math", "difficulty": .2, "concept": "addition", "reward": 5}


def test_daily_generation_and_submission_are_idempotent():
    from app.services.challenge_service import ChallengeService
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(User(id=1, username="a", hashed_password="x")); db.commit()
    rag = Rag(); service = ChallengeService(db, llm=Llm(), rag=rag, profile=Profile(), today=lambda: date(2026, 7, 11))
    challenge = service.generate(1, "math")
    assert service.generate(1, "math").id == challenge.id
    assert rag.calls == [("loops", 5)]
    assert service.submit(1, challenge.id, " 4 ")["is_correct"] is True
    assert service.submit(1, challenge.id, "4")["awarded_points"] == 5
    assert db.query(PointTransaction).filter_by(user_id=1).count() == 1
