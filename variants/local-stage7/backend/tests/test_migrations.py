from __future__ import annotations

import os
import subprocess

from sqlalchemy import create_engine, inspect


def run_alembic(database_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    return subprocess.run(
        [
            os.fspath(os.path.join(".venv", "Scripts", "python.exe")),
            "-m",
            "alembic",
            "-c",
            "alembic.ini",
            *args,
        ],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_alembic_upgrades_empty_database_and_downgrades(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    upgrade = run_alembic(database_url, "upgrade", "head")
    assert upgrade.returncode == 0, upgrade.stderr
    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert "users" in tables
    assert "student_profiles" in tables
    assert "alembic_version" in tables
    engine.dispose()

    downgrade = run_alembic(database_url, "downgrade", "base")
    assert downgrade.returncode == 0, downgrade.stderr
    engine = create_engine(database_url)
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    engine.dispose()
