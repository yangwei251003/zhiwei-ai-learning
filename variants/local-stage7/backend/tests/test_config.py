import pytest
from pydantic import ValidationError

from app.core.config import Settings


def valid_settings(**overrides):
    values = {
        "spark_api_key": "spark-test-key",
        "secret_key": "s" * 32,
        "cors_allowed_origins": "http://localhost:5173,http://localhost:3000",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_settings_require_real_secrets() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, spark_api_key="", secret_key="short")


def test_settings_parse_origins_and_model_levels() -> None:
    settings = valid_settings()
    assert settings.auto_create_tables is False
    assert settings.spark_timeout_seconds == 180
    assert settings.cors_origins == ["http://localhost:5173", "http://localhost:3000"]
    assert settings.model_for("high") == "generalv3.5"
    assert settings.model_for("medium") == "generalv3"
    assert settings.model_for("low") == "lite"
    with pytest.raises(ValueError, match="Unknown model level"):
        settings.model_for("ultra")


def test_spark_api_password_is_preferred_for_openai_compatible_bearer_auth() -> None:
    settings = valid_settings(
        spark_api_key="legacy-key", spark_api_password="openai-password"
    )
    assert settings.spark_bearer_token == "openai-password"
