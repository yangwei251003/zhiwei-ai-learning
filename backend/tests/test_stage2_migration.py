import json
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core import get_settings
from app.api.resources import delete_resource
from app.models import (
    AchievementDefinition,
    ChallengeSubmission,
    DailyChallenge,
    KnowledgeDocument,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    LearningResource,
    PointTransaction,
    ProfileChangeLog,
    ResourceLink,
    StudentProfile,
    StudentProfileVersion,
    User,
    UserAchievement,
)
from app.schemas import ProfileOut


BACKEND_DIR = Path(__file__).resolve().parents[1]
STAGE1_REVISION = "e27f9f829dda"


@pytest.fixture(autouse=True)
def _restore_settings_after_test(monkeypatch):
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


def _alembic_config(monkeypatch, database_path: Path) -> Config:
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _unique_column_sets(inspector, table_name: str) -> set[tuple[str, ...]]:
    return {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints(table_name)
    }


def test_upgrade_empty_database_creates_stage2_schema(tmp_path, monkeypatch):
    database_path = tmp_path / "empty.db"
    command.upgrade(_alembic_config(monkeypatch, database_path), "head")

    inspector = inspect(create_engine(f"sqlite:///{database_path.as_posix()}"))
    expected_tables = {
        "student_profile_versions",
        "profile_change_logs",
        "knowledge_documents",
        "resource_links",
        "knowledge_graph_nodes",
        "knowledge_graph_edges",
        "achievement_definitions",
        "user_achievements",
        "daily_challenges",
        "challenge_submissions",
        "point_transactions",
    }
    assert expected_tables <= set(inspector.get_table_names())

    profile_columns = {
        column["name"] for column in inspector.get_columns("student_profiles")
    }
    weak_points_column = next(
        column for column in inspector.get_columns("student_profiles")
        if column["name"] == "weak_points"
    )
    assert weak_points_column["nullable"] is False
    assert {
        "current_version",
        "learning_pace",
        "short_term_goal",
        "medium_term_goal",
        "knowledge_state",
        "weak_points",
        "energy_scores",
        "constellation_points",
    } <= profile_columns
    assert ("profile_id", "version") in _unique_column_sets(
        inspector, "student_profile_versions"
    )
    assert "user_id" not in {
        column["name"]
        for column in inspector.get_columns("student_profile_versions")
    }
    assert ("user_id", "course", "key") in _unique_column_sets(
        inspector, "knowledge_graph_nodes"
    )
    assert ("source_node_id", "target_node_id", "relation") in _unique_column_sets(
        inspector, "knowledge_graph_edges"
    )
    resource_link_targets = {
        foreign_key["referred_table"]
        for foreign_key in inspector.get_foreign_keys("resource_links")
    }
    assert "learning_resources" in resource_link_targets
    assert ("challenge_id",) in _unique_column_sets(
        inspector, "challenge_submissions"
    )
    assert "user_id" not in {
        column["name"] for column in inspector.get_columns("challenge_submissions")
    }


def test_alembic_check_has_no_model_drift(tmp_path, monkeypatch):
    database_path = tmp_path / "check.db"
    config = _alembic_config(monkeypatch, database_path)
    command.upgrade(config, "head")

    command.check(config)


def test_upgrade_from_stage1_preserves_existing_data(tmp_path, monkeypatch):
    database_path = tmp_path / "stage1.db"
    config = _alembic_config(monkeypatch, database_path)
    command.upgrade(config, STAGE1_REVISION)
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")

    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, username, hashed_password, role) "
                "VALUES (1, 'legacy', 'hash', 'student'), "
                "(2, 'json-list', 'hash', 'student'), "
                "(3, 'empty', 'hash', 'student')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO student_profiles "
                "(id, user_id, knowledge_base, weak_points, learning_goal) "
                "VALUES (1, 1, 'python', 'recursion', 'pass exam')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO student_profiles (id, user_id, weak_points) VALUES "
                "(2, 2, :points), (3, 3, NULL)"
            ),
            {
                "points": json.dumps(
                    ["graphs", {"name": "algebra", "confidence": 0.8}, {"name": "sql"}]
                )
            },
        )
        connection.execute(
            text(
                "INSERT INTO learning_resources "
                "(id, user_id, resource_type, title, content) "
                "VALUES (1, 1, 'document', 'Legacy note', 'body')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO learning_paths (id, user_id, path_data) "
                "VALUES (1, 1, '[]')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO conversations (id, user_id, role, content) "
                "VALUES (1, 1, 'user', 'hello')"
            )
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        assert connection.execute(text("SELECT username FROM users WHERE id=1")).scalar() == "legacy"
        profile = connection.execute(
            text(
                "SELECT knowledge_base, weak_points, learning_goal, current_version "
                "FROM student_profiles WHERE id=1"
            )
        ).one()
        assert profile.knowledge_base == "python"
        assert json.loads(profile.weak_points) == [
            {"name": "recursion", "confidence": 0.5}
        ]
        normalized_list = json.loads(
            connection.execute(
                text("SELECT weak_points FROM student_profiles WHERE id=2")
            ).scalar()
        )
        assert normalized_list == [
            {"name": "graphs", "confidence": 0.5},
            {"name": "algebra", "confidence": 0.8},
            {"name": "sql", "confidence": 0.5},
        ]
        assert json.loads(
            connection.execute(
                text("SELECT weak_points FROM student_profiles WHERE id=3")
            ).scalar()
        ) == []
        assert profile.learning_goal == "pass exam"
        assert profile.current_version == 1
        assert connection.execute(text("SELECT title FROM learning_resources WHERE id=1")).scalar() == "Legacy note"
        assert connection.execute(text("SELECT count(*) FROM learning_paths")).scalar() == 1
        assert connection.execute(text("SELECT content FROM conversations WHERE id=1")).scalar() == "hello"
        assert "knowledge_documents" in inspect(connection).get_table_names()

    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        profile_model = session.get(StudentProfile, 1)
        assert profile_model.weak_points == [{"name": "recursion", "confidence": 0.5}]
        profile_model.weak_points = ["recursion", {"name": "dynamic programming"}]
        session.commit()
        session.expire_all()
        assert session.get(StudentProfile, 1).weak_points == [
            {"name": "recursion", "confidence": 0.5},
            {"name": "dynamic programming", "confidence": 0.5},
        ]
        session.get(StudentProfile, 1).weak_points.append(
            {"name": "graphs", "confidence": 0.6}
        )
        session.commit()
        session.expire_all()
        assert session.get(StudentProfile, 1).weak_points[-1] == {
            "name": "graphs",
            "confidence": 0.6,
        }


def test_profile_schema_requires_confidence_weak_points():
    profile = ProfileOut(
        weak_points=[{"name": "recursion", "confidence": 0.75}]
    )
    assert profile.weak_points[0].name == "recursion"
    assert profile.weak_points[0].confidence == 0.75
    with pytest.raises(ValueError):
        ProfileOut(weak_points=[{"name": "invalid", "confidence": 1.1}])


def test_stage2_json_fields_round_trip(tmp_path, monkeypatch):
    database_path = tmp_path / "json.db"
    command.upgrade(_alembic_config(monkeypatch, database_path), "head")
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        user = User(username="json-user", hashed_password="hash")
        session.add(user)
        session.flush()
        profile = StudentProfile(
            user_id=user.id,
            weak_points=[{"name": "loops", "confidence": 0.4}],
            knowledge_state={"loops": "learning"},
            energy_scores={"focus": 0.9},
            constellation_points={"python": 12},
        )
        conversation_id = 1
        session.execute(
            text(
                "INSERT INTO conversations (id, user_id, role, content) "
                "VALUES (:id, :user_id, 'user', 'update profile')"
            ),
            {"id": conversation_id, "user_id": user.id},
        )
        source = LearningResource(
            user_id=user.id, resource_type="document", title="Source", content="a"
        )
        target = LearningResource(
            user_id=user.id, resource_type="quiz", title="Target", content="b"
        )
        session.add_all([profile, source, target])
        session.flush()
        version = StudentProfileVersion(
            profile_id=profile.id,
            version=1,
            snapshot={"weak_points": profile.weak_points},
            source_conversation_id=conversation_id,
        )
        document = KnowledgeDocument(
            user_id=user.id,
            course="python",
            original_filename="notes.pdf",
            storage_name="stored-notes.pdf",
            mime="application/pdf",
            size=128,
            status="ready",
            keywords=["loops", "functions"],
        )
        link = ResourceLink(
            user_id=user.id,
            source_resource_id=source.id,
            target_resource_id=target.id,
            relation="practices",
            metadata_json={"chapter": 2},
        )
        node_a = KnowledgeGraphNode(
            user_id=user.id,
            course="python",
            key="loops",
            label="Loops",
            resource_ids=[source.id],
            metadata_json={"x": 1},
        )
        node_b = KnowledgeGraphNode(
            user_id=user.id,
            course="python",
            key="functions",
            label="Functions",
            resource_ids=[target.id],
            metadata_json={"x": 2},
        )
        achievement = AchievementDefinition(
            code="first-loop",
            title="First loop",
            rule_type="count",
            threshold=1,
        )
        challenge = DailyChallenge(
            user_id=user.id,
            course="python",
            challenge_date=date(2026, 7, 11),
            question_type="choice",
            question="Loop keyword?",
            options=["for", "class"],
            answer="for",
            concept="loops",
        )
        session.add_all([version, document, link, node_a, node_b, achievement, challenge])
        session.flush()
        session.add_all(
            [
                ProfileChangeLog(
                    profile_version_id=version.id,
                    conversation_id=conversation_id,
                    changes={"weak_points": {"added": ["loops"]}},
                ),
                KnowledgeGraphEdge(
                    user_id=user.id,
                    course="python",
                    source_node_id=node_a.id,
                    target_node_id=node_b.id,
                    relation="prerequisite",
                    metadata_json={"verified": True},
                ),
                UserAchievement(
                    user_id=user.id, achievement_id=achievement.id, progress=1
                ),
                ChallengeSubmission(
                    challenge_id=challenge.id,
                    answer="for",
                    is_correct=True,
                    awarded_points=5,
                ),
                PointTransaction(
                    user_id=user.id,
                    delta=5,
                    reason="daily challenge",
                    reference_type="challenge",
                    reference_id=challenge.id,
                    idempotency_key="challenge-1",
                ),
            ]
        )
        session.commit()
        session.expire_all()

        assert profile.knowledge_state == {"loops": "learning"}
        assert profile.energy_scores == {"focus": 0.9}
        assert profile.constellation_points == {"python": 12}
        assert version.snapshot == {"weak_points": [{"name": "loops", "confidence": 0.4}]}
        assert version.change_logs[0].changes == {"weak_points": {"added": ["loops"]}}
        assert document.keywords == ["loops", "functions"]
        assert link.metadata_json == {"chapter": 2}
        assert node_a.resource_ids == [source.id]
        assert node_a.metadata_json == {"x": 1}
        assert challenge.options == ["for", "class"]
        assert session.query(KnowledgeGraphEdge).one().metadata_json == {"verified": True}
        assert session.query(PointTransaction).one().delta == 5


def test_graph_edges_reject_cross_tenant_nodes(tmp_path, monkeypatch):
    database_path = tmp_path / "tenant.db"
    command.upgrade(_alembic_config(monkeypatch, database_path), "head")
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
        connection.execute(
            text(
                "INSERT INTO users (id, username, hashed_password) VALUES "
                "(1, 'one', 'h'), (2, 'two', 'h')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO knowledge_graph_nodes "
                "(id,user_id,course,key,label,difficulty,mastery,status,resource_ids,metadata) VALUES "
                "(1,1,'python','a','A',0,0,'open','[]','{}'), "
                "(2,2,'python','b','B',0,0,'open','[]','{}')"
            )
        )
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO knowledge_graph_edges "
                    "(user_id,course,source_node_id,target_node_id,relation,weight,metadata) "
                    "VALUES (1,'python',1,2,'prerequisite',1,'{}')"
                )
            )
        connection.execute(
            text(
                "INSERT INTO knowledge_graph_nodes "
                "(id,user_id,course,key,label,difficulty,mastery,status,resource_ids,metadata) "
                "VALUES (3,1,'java','c','C',0,0,'open','[]','{}')"
            )
        )
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO knowledge_graph_edges "
                    "(user_id,course,source_node_id,target_node_id,relation,weight,metadata) "
                    "VALUES (1,'python',1,3,'prerequisite',1,'{}')"
                )
            )


def test_resource_links_enforce_tenant_and_cascade_deletes(tmp_path, monkeypatch):
    database_path = tmp_path / "resource-links.db"
    command.upgrade(_alembic_config(monkeypatch, database_path), "head")
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        first = User(username="first", hashed_password="h")
        second = User(username="second", hashed_password="h")
        session.add_all([first, second])
        session.flush()
        source = LearningResource(
            user_id=first.id, resource_type="document", title="source", content="a"
        )
        same_tenant_target = LearningResource(
            user_id=first.id, resource_type="quiz", title="target", content="b"
        )
        other_tenant_target = LearningResource(
            user_id=second.id, resource_type="quiz", title="other", content="c"
        )
        session.add_all([source, same_tenant_target, other_tenant_target])
        session.commit()

        session.add(
            ResourceLink(
                user_id=first.id,
                source_resource_id=source.id,
                target_resource_id=other_tenant_target.id,
                relation="invalid",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        link = ResourceLink(
            user_id=first.id,
            source_resource_id=source.id,
            target_resource_id=same_tenant_target.id,
            relation="practices",
        )
        session.add(link)
        session.commit()
        assert session.query(ResourceLink).count() == 1

        result = delete_resource(source.id, first, session)
        assert result == {"message": "删除成功"}
        assert session.query(ResourceLink).count() == 0
        session.expunge(link)

        replacement_source = LearningResource(
            user_id=first.id,
            resource_type="document",
            title="replacement",
            content="d",
        )
        session.add(replacement_source)
        session.flush()
        session.add(
            ResourceLink(
                user_id=first.id,
                source_resource_id=replacement_source.id,
                target_resource_id=same_tenant_target.id,
                relation="targets",
            )
        )
        session.commit()
        result = delete_resource(same_tenant_target.id, first, session)
        assert result == {"message": "删除成功"}
        assert session.query(ResourceLink).count() == 0


def test_stage2_datetime_columns_are_timezone_aware():
    expected = {
        StudentProfileVersion: ["created_at"],
        ProfileChangeLog: ["created_at"],
        KnowledgeDocument: ["created_at", "updated_at"],
        ResourceLink: ["created_at"],
        UserAchievement: ["unlocked_at"],
        ChallengeSubmission: ["submitted_at"],
        PointTransaction: ["created_at"],
    }
    for model, column_names in expected.items():
        for column_name in column_names:
            assert model.__table__.c[column_name].type.timezone is True

    defaulted_columns = {
        StudentProfileVersion: ["created_at"],
        ProfileChangeLog: ["created_at"],
        KnowledgeDocument: ["created_at", "updated_at"],
        ResourceLink: ["created_at"],
        ChallengeSubmission: ["submitted_at"],
        PointTransaction: ["created_at"],
    }
    for model, column_names in defaulted_columns.items():
        for column_name in column_names:
            value = model.__table__.c[column_name].default.arg(None)
            assert value.tzinfo is not None
            assert value.utcoffset().total_seconds() == 0


def test_downgrade_returns_to_stage1_schema(tmp_path, monkeypatch):
    database_path = tmp_path / "downgrade.db"
    config = _alembic_config(monkeypatch, database_path)
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id,username,hashed_password) VALUES (1,'kept','h')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO student_profiles (id,user_id,weak_points) "
                "VALUES (1,1,:points)"
            ),
            {"points": json.dumps([{"name": "loops", "confidence": 0.5}])},
        )
        connection.execute(
            text(
                "INSERT INTO learning_resources (id,user_id,resource_type,title,content) "
                "VALUES (1,1,'document','kept resource','body')"
            )
        )
        connection.execute(
            text("INSERT INTO learning_paths (id,user_id,path_data) VALUES (1,1,'[]')")
        )
        connection.execute(
            text(
                "INSERT INTO conversations (id,user_id,role,content) "
                "VALUES (1,1,'user','kept conversation')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO student_profile_versions "
                "(id,profile_id,version,snapshot,created_at) "
                "VALUES (1,1,1,'{}','2026-07-11')"
            )
        )
    command.downgrade(config, STAGE1_REVISION)

    inspector = inspect(engine)
    assert "student_profile_versions" not in inspector.get_table_names()
    profile_columns = {
        column["name"] for column in inspector.get_columns("student_profiles")
    }
    assert "current_version" not in profile_columns
    assert "weak_points" in profile_columns
    with engine.connect() as connection:
        assert connection.execute(text("SELECT username FROM users")).scalar() == "kept"
        assert connection.execute(text("SELECT count(*) FROM student_profiles")).scalar() == 1
        assert connection.execute(text("SELECT title FROM learning_resources")).scalar() == "kept resource"
        assert connection.execute(text("SELECT count(*) FROM learning_paths")).scalar() == 1
        assert connection.execute(text("SELECT content FROM conversations")).scalar() == "kept conversation"
