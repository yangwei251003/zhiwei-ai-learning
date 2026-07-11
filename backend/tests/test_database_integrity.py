import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.core.database import engine as application_engine


def test_all_sqlite_connections_enable_foreign_keys(tmp_path):
    with application_engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1

    engine = create_engine(f"sqlite:///{(tmp_path / 'foreign-keys.db').as_posix()}")
    with engine.begin() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
        connection.execute(text("CREATE TABLE parents (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE children ("
                "id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parents(id))"
            )
        )
        with pytest.raises(IntegrityError):
            connection.execute(
                text("INSERT INTO children (id, parent_id) VALUES (1, 999)")
            )
