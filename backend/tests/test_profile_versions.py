import pytest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import Conversation, ProfileChangeLog, StudentProfileVersion, User
from app.schemas import ProfilePatch
from app.services.profile_service import (
    ProfileConflictError,
    ProfileService,
    ProfileSourceNotFound,
    ProfileVersionNotFound,
)


@pytest.fixture
def profile_db(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'profiles.db').as_posix()}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        user = User(username="profile-user", hashed_password="hash")
        session.add(user)
        session.commit()
        yield session, user
    engine.dispose()


def test_get_or_create_persists_initial_snapshot(profile_db):
    db, user = profile_db
    profile = ProfileService(db).get_or_create(user.id)

    assert profile.current_version == 1
    version = db.scalar(select(StudentProfileVersion))
    assert version.version == 1
    assert version.snapshot["learning_pace"] == "medium"
    assert version.snapshot["energy_scores"] == profile.energy_scores
    assert version.snapshot["constellation_points"] == profile.constellation_points
    assert len(profile.energy_scores) == 7


def test_update_only_changes_provided_fields_and_records_before_after(profile_db):
    db, user = profile_db
    service = ProfileService(db)
    original = service.get_or_create(user.id)

    updated = service.update(
        user.id,
        ProfilePatch(
            major="  Computer Science  ",
            weak_points=[{"name": "  recursion ", "confidence": 0.8}],
        ),
        reason="manual correction",
    )

    assert updated.current_version == 2
    assert updated.major == "Computer Science"
    assert updated.cognitive_style == original.cognitive_style
    assert updated.weak_points == [{"name": "recursion", "confidence": 0.8}]
    change = db.scalar(select(ProfileChangeLog))
    assert change.reason == "manual correction"
    assert change.changes["major"] == {
        "before": "",
        "after": "Computer Science",
    }


def test_noop_update_does_not_create_version_or_change_log(profile_db):
    db, user = profile_db
    service = ProfileService(db)
    service.get_or_create(user.id)

    result = service.update(
        user.id, ProfilePatch(cognitive_style="visual"), reason="same value"
    )

    assert result.current_version == 1
    assert db.scalar(select(func.count(StudentProfileVersion.id))) == 1
    assert db.scalar(select(func.count(ProfileChangeLog.id))) == 0


def test_patch_rejects_invalid_profile_values():
    with pytest.raises(ValidationError):
        ProfilePatch(cognitive_style="reading")
    with pytest.raises(ValidationError):
        ProfilePatch(learning_pace="instant")
    with pytest.raises(ValidationError):
        ProfilePatch(weak_points=[{"name": "loops", "confidence": 1.1}])


def test_rollback_creates_a_new_immutable_version(profile_db):
    db, user = profile_db
    service = ProfileService(db)
    service.get_or_create(user.id)
    service.update(user.id, ProfilePatch(major="Math"), reason="first")
    target_snapshot = db.scalar(
        select(StudentProfileVersion.snapshot).where(
            StudentProfileVersion.version == 1
        )
    )

    rolled_back = service.rollback(user.id, 1, reason="restore baseline")

    assert rolled_back.current_version == 3
    assert rolled_back.major == ""
    versions = service.versions(user.id)
    assert [item.version for item in versions] == [3, 2, 1]
    assert versions[-1].snapshot == target_snapshot
    assert versions[0].snapshot == target_snapshot
    latest_change = service.changes(user.id)[0]
    assert latest_change.reason == "restore baseline"
    assert latest_change.changes["major"] == {"before": "Math", "after": ""}

    with pytest.raises(ProfileVersionNotFound):
        service.rollback(user.id, 99, reason="missing")


def test_visualization_is_stable_bounded_and_persisted(profile_db):
    db, user = profile_db
    service = ProfileService(db)
    service.update(
        user.id,
        ProfilePatch(
            major="Software Engineering",
            interests="AI",
            weak_points=[{"name": "graphs", "confidence": 0.75}],
        ),
        reason="seed",
    )

    first = service.visualization(user.id)
    db.expire_all()
    second = service.visualization(user.id)

    assert first == second
    assert len(first["energy_scores"]) == 7
    assert all(0 <= score <= 100 for score in first["energy_scores"].values())
    assert set(first["constellation_points"]) == set(first["energy_scores"])
    profile = service.current(user.id)
    assert profile.energy_scores == first["energy_scores"]
    current_snapshot = db.scalar(
        select(StudentProfileVersion.snapshot).where(
            StudentProfileVersion.profile_id == profile.id,
            StudentProfileVersion.version == profile.current_version,
        )
    )
    assert current_snapshot["energy_scores"] == profile.energy_scores
    assert current_snapshot["constellation_points"] == profile.constellation_points


def test_visualization_and_export_are_read_only_when_current_snapshot_is_complete(
    profile_db,
):
    db, user = profile_db
    service = ProfileService(db)
    profile = service.get_or_create(user.id)
    before_version = profile.current_version
    before_versions = db.scalar(select(func.count(StudentProfileVersion.id)))

    service.visualization(user.id)
    service.export_markdown(user.id)

    assert service.current(user.id).current_version == before_version
    assert db.scalar(select(func.count(StudentProfileVersion.id))) == before_versions
    assert db.scalar(select(func.count(ProfileChangeLog.id))) == 0


def test_visualization_repairs_legacy_missing_data_with_a_complete_version(profile_db):
    db, user = profile_db
    service = ProfileService(db)
    profile = service.get_or_create(user.id)
    profile.energy_scores = {}
    profile.constellation_points = {}
    db.commit()

    result = service.visualization(user.id)

    db.refresh(profile)
    assert profile.current_version == 2
    assert result["energy_scores"] == profile.energy_scores
    repaired = db.scalar(
        select(StudentProfileVersion).where(
            StudentProfileVersion.profile_id == profile.id,
            StudentProfileVersion.version == 2,
        )
    )
    assert repaired.snapshot["energy_scores"] == profile.energy_scores
    assert repaired.snapshot["constellation_points"] == profile.constellation_points
    change = db.scalar(
        select(ProfileChangeLog).where(
            ProfileChangeLog.profile_version_id == repaired.id
        )
    )
    assert "energy_scores" in change.changes
    assert "constellation_points" in change.changes


def test_export_markdown_contains_profile_and_recent_changes_but_no_password(profile_db):
    db, user = profile_db
    service = ProfileService(db)
    service.update(
        user.id,
        ProfilePatch(major="Physics", weak_points=[{"name": "vectors"}]),
        reason="assessment",
    )

    document = service.export_markdown(user.id)

    assert user.username in document
    assert "当前版本：2" in document
    assert "七维画像" in document
    assert "能量数据" in document
    assert "vectors" in document
    assert "assessment" in document
    assert user.hashed_password not in document


def test_concurrent_updates_use_compare_and_swap_without_lost_data(tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'concurrent.db').as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 1},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as setup:
        user = User(username="concurrent", hashed_password="hash")
        setup.add(user)
        setup.commit()
        user_id = user.id
        ProfileService(setup).get_or_create(user_id)

    barrier = Barrier(2)
    original_cas = ProfileService._cas_write

    def synchronized_cas(self, *args, **kwargs):
        barrier.wait(timeout=5)
        return original_cas(self, *args, **kwargs)

    ProfileService._cas_write = synchronized_cas
    try:
        def write(patch, reason):
            with factory() as session:
                try:
                    result = ProfileService(session).update(
                        user_id, patch, reason=reason
                    )
                    return ("ok", result.major, result.interests)
                except ProfileConflictError:
                    return ("conflict", "", "")

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    lambda args: write(*args),
                    [
                        (ProfilePatch(major="Mathematics"), "major writer"),
                        (ProfilePatch(interests="Robotics"), "interest writer"),
                    ],
                )
            )

        assert sorted(item[0] for item in results) == ["conflict", "ok"]

        with factory() as verify:
            current = ProfileService(verify).current(user_id)
            assert current.current_version == 2
            assert (current.major, current.interests) in {
                ("Mathematics", ""),
                ("", "Robotics"),
            }
            assert [v.version for v in ProfileService(verify).versions(user_id)] == [2, 1]
    finally:
        ProfileService._cas_write = original_cas
        engine.dispose()


def test_source_conversation_must_belong_to_profile_user(profile_db):
    db, user = profile_db
    other = User(username="other-source", hashed_password="hash")
    db.add(other)
    db.flush()
    own = Conversation(user_id=user.id, role="user", content="own")
    foreign = Conversation(user_id=other.id, role="user", content="foreign")
    db.add_all([own, foreign])
    db.commit()
    service = ProfileService(db)

    service.update(
        user.id,
        ProfilePatch(major="Physics"),
        source_conversation_id=own.id,
        reason="owned source",
    )
    with pytest.raises(ProfileSourceNotFound):
        service.update(
            user.id,
            ProfilePatch(major="Chemistry"),
            source_conversation_id=foreign.id,
            reason="foreign source",
        )
    with pytest.raises(ProfileSourceNotFound):
        service.rollback(
            user.id,
            1,
            source_conversation_id=foreign.id,
            reason="foreign rollback",
        )


def test_export_markdown_escapes_untrusted_inline_values(profile_db):
    db, user = profile_db
    user.username = "mallory\n# injected <script>"
    db.commit()
    service = ProfileService(db)
    service.update(
        user.id,
        ProfilePatch(
            major="[click](javascript:alert(1))",
            weak_points=[{"name": "x\n## forged <img src=x>", "confidence": 0.5}],
        ),
        reason="ok\n# forged [link](https://bad.example)",
    )

    document = service.export_markdown(user.id)

    assert "\n# injected" not in document
    assert "\n## forged" not in document
    assert "<script>" not in document
    assert "<img" not in document
    assert "[click](javascript:" not in document
    assert "[link](https://" not in document
    assert "&lt;script&gt;" in document
    assert "\\[click\\]\\(javascript:alert\\(1\\)\\)" in document
