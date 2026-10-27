from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.database import Base, build_engine
from app.models.database import StudentProfile, User


def test_all_stage_one_tables_are_created(tmp_path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    assert set(inspect(engine).get_table_names()) == {
        "achievements",
        "conversations",
        "knowledge_chunks",
        "knowledge_documents",
        "learning_path_steps",
        "learning_paths",
        "messages",
        "resources",
        "student_profiles",
        "system_settings",
        "user_achievements",
        "users",
    }
    engine.dispose()


def test_user_profile_relationship_round_trip(tmp_path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(
            username="learner", email="learner@example.com", hashed_password="hash"
        )
        user.profile = StudentProfile(
            knowledge_base="beginner", learning_goal="learn Python"
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        assert user.profile.learning_goal == "learn Python"
    engine.dispose()
