from pathlib import Path


def test_alembic_uses_settings_url_without_configparser_interpolation():
    """Percent-encoded database passwords must reach SQLAlchemy unchanged."""
    source = (Path(__file__).parents[1] / "alembic" / "env.py").read_text(
        encoding="utf-8"
    )

    assert "create_engine(settings.database_url" in source
    assert "engine_from_config" not in source
