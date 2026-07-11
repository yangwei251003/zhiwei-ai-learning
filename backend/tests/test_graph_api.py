import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import User


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all([User(id=1, username="a", hashed_password="x"), User(id=2, username="b", hashed_password="x")])
    session.commit()
    yield session
    session.close()


def test_graph_upsert_is_idempotent_and_rejects_prerequisite_cycle(db):
    from app.services.graph_service import GraphCycleError, GraphService
    service = GraphService(db)
    first = service.upsert_node(1, "python", {"key": "loop", "label": "Loop"})
    assert service.upsert_node(1, "python", {"key": "loop", "label": "Loops"}).id == first.id
    condition = service.upsert_node(1, "python", {"key": "condition", "label": "Condition"})
    service.upsert_edge(1, "python", first.id, condition.id, "prerequisite")
    with pytest.raises(GraphCycleError):
        service.upsert_edge(1, "python", condition.id, first.id, "prerequisite")


def test_graph_never_exposes_another_tenant(db):
    from app.services.graph_service import GraphNotFound, GraphService
    node = GraphService(db).upsert_node(1, "python", {"key": "loop", "label": "Loop"})
    with pytest.raises(GraphNotFound):
        GraphService(db).get_node(2, "python", node.id)


def test_graph_mastery_update_evaluates_typed_achievement(db):
    from app.services.graph_service import GraphService
    class Achievements:
        def __init__(self): self.calls=[]
        def evaluate(self, *args): self.calls.append(args)
    achievements=Achievements(); service=GraphService(db, achievement_service=achievements)
    service.upsert_node(1, "python", {"key":"loop", "label":"Loop", "mastery":1})
    assert achievements.calls[-1] == (1, "graph_mastery_updated", {"mastered_nodes": 1})
