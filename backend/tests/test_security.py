"""Unit tests for security primitives — run without a database."""

import uuid

import jwt as pyjwt
import pytest

from app.core import security


def test_password_hash_and_verify():
    h = security.hash_password("correct-horse-9")
    assert h != "correct-horse-9"
    assert security.verify_password("correct-horse-9", h)
    assert not security.verify_password("wrong-password-1", h)


def test_access_token_roundtrip():
    user_id = uuid.uuid4()
    token = security.create_access_token(user_id)
    payload = security.decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert "exp" in payload and "jti" in payload


def test_access_token_tampered_rejected():
    token = security.create_access_token(uuid.uuid4())
    with pytest.raises(pyjwt.PyJWTError):
        security.decode_access_token(token[:-2] + "xx")


def test_refresh_token_only_hash_stored():
    raw, token_hash = security.generate_refresh_token()
    assert raw != token_hash
    assert len(token_hash) == 64  # sha256 hex
    assert security.hash_refresh_token(raw) == token_hash
