from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.core.database import Base, build_engine, build_session_factory
from app.core.security import verify_password
from app.models.database import User
from app.services.admin_bootstrap import AdminBootstrapError, bootstrap_admin
from scripts.bootstrap_admin import run


def bootstrap_context(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'bootstrap.db'}")
    Base.metadata.create_all(engine)
    return engine, build_session_factory(engine)


def test_bootstrap_creates_one_active_admin_with_hashed_password(tmp_path) -> None:
    engine, factory = bootstrap_context(tmp_path)

    result = bootstrap_admin(
        factory,
        username="stage5admin",
        email="stage5admin@example.com",
        password="AdminPass123!",
    )

    assert result.username == "stage5admin"
    assert result.email == "stage5admin@example.com"
    with factory() as db:
        user = db.scalar(select(User).where(User.email == "stage5admin@example.com"))
        assert user is not None
        assert user.is_admin is True
        assert user.is_active is True
        assert user.hashed_password != "AdminPass123!"
        assert verify_password("AdminPass123!", user.hashed_password)
    engine.dispose()


def test_bootstrap_refuses_to_replace_an_existing_admin(tmp_path) -> None:
    engine, factory = bootstrap_context(tmp_path)
    bootstrap_admin(
        factory,
        username="firstadmin",
        email="firstadmin@example.com",
        password="AdminPass123!",
    )

    with pytest.raises(AdminBootstrapError, match="管理员已存在"):
        bootstrap_admin(
            factory,
            username="secondadmin",
            email="secondadmin@example.com",
            password="OtherPass123!",
        )

    with factory() as db:
        assert len(db.scalars(select(User).where(User.is_admin.is_(True))).all()) == 1
    engine.dispose()


@pytest.mark.parametrize(
    ("username", "email", "password", "message"),
    [
        ("a", "admin@example.com", "AdminPass123!", "用户名"),
        ("admin", "not-an-email", "AdminPass123!", "邮箱"),
        ("admin", "admin@example.com", "short", "密码"),
    ],
)
def test_bootstrap_validates_credentials_before_writing(
    tmp_path, username, email, password, message
) -> None:
    engine, factory = bootstrap_context(tmp_path)

    with pytest.raises(AdminBootstrapError, match=message):
        bootstrap_admin(factory, username=username, email=email, password=password)

    with factory() as db:
        assert db.scalar(select(User)) is None
    engine.dispose()


def test_bootstrap_cli_reads_password_twice_without_printing_it(
    tmp_path, capsys
) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli.db'}"
    engine = build_engine(database_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    settings = Settings(
        _env_file=None,
        spark_api_key="test-key",
        secret_key="x" * 32,
        database_url=database_url,
    )
    answers = iter(["AdminPass123!", "AdminPass123!"])

    exit_code = run(
        ["--username", "cliadmin", "--email", "cliadmin@example.com"],
        settings=settings,
        password_reader=lambda _: next(answers),
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "cliadmin@example.com" in captured.out
    assert "AdminPass123!" not in captured.out + captured.err


def test_bootstrap_cli_refuses_unmigrated_database(tmp_path, capsys) -> None:
    settings = Settings(
        _env_file=None,
        spark_api_key="test-key",
        secret_key="x" * 32,
        database_url=f"sqlite:///{tmp_path / 'unmigrated.db'}",
    )

    exit_code = run(
        ["--username", "cliadmin", "--email", "cliadmin@example.com"],
        settings=settings,
        password_reader=lambda _: "AdminPass123!",
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "alembic upgrade head" in captured.err
