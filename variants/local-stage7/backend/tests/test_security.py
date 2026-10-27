from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


SETTINGS = Settings(_env_file=None, spark_api_key="test-key", secret_key="x" * 32)


def test_password_hash_is_salted_and_verifiable() -> None:
    first = hash_password("StrongPass123!")
    second = hash_password("StrongPass123!")
    assert first != second
    assert verify_password("StrongPass123!", first)
    assert not verify_password("wrong", first)


def test_jwt_round_trip_and_tamper_rejection() -> None:
    token = create_access_token("42", SETTINGS)
    assert decode_access_token(token, SETTINGS) == 42
    with pytest.raises(HTTPException) as error:
        decode_access_token(token + "tampered", SETTINGS)
    assert error.value.status_code == 401


def test_expired_jwt_is_rejected() -> None:
    token = create_access_token("42", SETTINGS, expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as error:
        decode_access_token(token, SETTINGS)
    assert error.value.status_code == 401
