import pytest

from app.core import Settings


def test_secret_key_is_required(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValueError, match="secret_key|SECRET_KEY"):
        Settings(_env_file=None)
