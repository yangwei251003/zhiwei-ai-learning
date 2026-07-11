from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import PointTransaction, User


def test_repeated_event_unlocks_and_awards_only_once():
    from app.services.achievement_service import AchievementService
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(User(id=1, username="a", hashed_password="x")); db.commit()
    service = AchievementService(db)
    service.evaluate(1, "chat_completed", {})
    service.evaluate(1, "chat_completed", {})
    unlocked = [item for item in service.list_for_user(1) if item["code"] == "first_chat"]
    assert unlocked[0]["unlocked"] is True
    assert db.query(PointTransaction).filter_by(user_id=1).count() == 1


def test_event_and_typed_metrics_must_match():
    from app.services.achievement_service import AchievementService
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)(); db.add(User(id=1, username="a", hashed_password="x")); db.commit()
    service = AchievementService(db)
    service.evaluate(1, "wrong_event", {"chat_completed": True, "resource_types": list("abcde")})
    service.evaluate(1, "resources_generated", {"resource_types": ["document"] * 5})
    rows = {x["code"]: x for x in service.list_for_user(1)}
    assert not rows["first_chat"]["unlocked"]
    assert not rows["five_resources"]["unlocked"]
    service.evaluate(1, "resources_generated", {"resource_types": ["document", "mindmap", "quiz", "video_script", "code_case"]})
    assert next(x for x in service.list_for_user(1) if x["code"] == "five_resources")["unlocked"]


def test_unrelated_events_do_not_reset_progress_and_progress_never_decreases():
    from app.services.achievement_service import AchievementService
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)(); db.add(User(id=1, username="a", hashed_password="x")); db.commit()
    service = AchievementService(db)
    service.evaluate(1, "graph_mastery_updated", {"mastered_nodes": 6})
    service.evaluate(1, "chat_completed", {})
    service.evaluate(1, "graph_mastery_updated", {"mastered_nodes": 2})
    graph = next(x for x in service.list_for_user(1) if x["code"] == "ten_graph_nodes")
    assert graph["progress"] == .6
