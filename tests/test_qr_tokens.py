from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.security.qr_tokens import (
    ENTRY_QR_PURPOSE,
    EXIT_QR_PURPOSE,
    create_entry_qr_token,
    create_exit_qr_token,
    decode_entry_qr_token,
    decode_exit_qr_token,
)
from app.security.tokens import ALGORITHM

TEST_SECRET = "test-secret-key-for-qr-tokens-at-least-32-bytes"


def test_create_entry_qr_token_contains_expected_data(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    token, expires_at = create_entry_qr_token(
        user_id=10,
        plate="ABC123",
        parking_lot_id="tornavias",
    )

    payload = decode_entry_qr_token(token)

    assert payload is not None
    assert payload["sub"] == "10"
    assert payload["plate"] == "ABC123"
    assert payload["parking_lot_id"] == "tornavias"
    assert payload["purpose"] == ENTRY_QR_PURPOSE
    assert payload["jti"]
    assert payload["exp"] - payload["iat"] == 300

    token_expiration = datetime.fromtimestamp(
        payload["exp"],
        timezone.utc,
    )

    assert token_expiration == expires_at.replace(microsecond=0)


def test_each_entry_qr_token_has_unique_jti(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    first_token, _ = create_entry_qr_token(
        user_id=10,
        plate="ABC123",
        parking_lot_id="tornavias",
    )

    second_token, _ = create_entry_qr_token(
        user_id=10,
        plate="ABC123",
        parking_lot_id="tornavias",
    )

    first_payload = decode_entry_qr_token(first_token)
    second_payload = decode_entry_qr_token(second_token)

    assert first_payload["jti"] != second_payload["jti"]


def test_decode_rejects_expired_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    now = datetime.now(timezone.utc)

    payload = {
        "sub": "10",
        "plate": "ABC123",
        "parking_lot_id": "tornavias",
        "purpose": ENTRY_QR_PURPOSE,
        "jti": "expired-test-token",
        "iat": now - timedelta(minutes=10),
        "exp": now - timedelta(minutes=5),
    }

    token = jwt.encode(
        payload,
        TEST_SECRET,
        algorithm=ALGORITHM,
    )

    assert decode_entry_qr_token(token) is None


def test_decode_rejects_wrong_purpose(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    now = datetime.now(timezone.utc)

    payload = {
        "sub": "10",
        "plate": "ABC123",
        "parking_lot_id": "tornavias",
        "purpose": "parking_exit",
        "jti": "wrong-purpose-token",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }

    token = jwt.encode(
        payload,
        TEST_SECRET,
        algorithm=ALGORITHM,
    )

    assert decode_entry_qr_token(token) is None


def test_decode_rejects_invalid_signature(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    token, _ = create_entry_qr_token(
        user_id=10,
        plate="ABC123",
        parking_lot_id="tornavias",
    )

    invalid_token = jwt.encode(
        {"sub": "10"},
        "another-test-secret-key-at-least-32-bytes",
        algorithm=ALGORITHM,
    )

    assert decode_entry_qr_token(invalid_token) is None
    assert decode_entry_qr_token(token) is not None


def test_create_entry_qr_token_requires_secret_key(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError):
        create_entry_qr_token(
            user_id=10,
            plate="ABC123",
            parking_lot_id="tornavias",
        )


def test_create_exit_qr_token_contains_expected_data(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    token, expires_at = create_exit_qr_token(
        user_id=10,
        parked_vehicle_id=777,
	plate="ABC123",
        parking_lot_id="tornavias",
    )

    payload = decode_exit_qr_token(token)

    assert payload is not None
    assert payload["sub"] == "10"
    assert payload["plate"] == "ABC123"
    assert payload["parking_lot_id"] == "tornavias"
    assert payload["purpose"] == EXIT_QR_PURPOSE
    assert payload["jti"]
    assert payload["exp"] - payload["iat"] == 300

    from datetime import datetime, timezone

    token_expiration = datetime.fromtimestamp(
        payload["exp"],
        timezone.utc,
    )

    assert token_expiration == expires_at.replace(microsecond=0)


def test_entry_and_exit_tokens_are_not_interchangeable(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    entry_token, _ = create_entry_qr_token(
        user_id=10,
        plate="ABC123",
        parking_lot_id="tornavias",
    )

    exit_token, _ = create_exit_qr_token(
        user_id=10,
	parked_vehicle_id=777,
        plate="ABC123",
        parking_lot_id="tornavias",
    )

    assert decode_exit_qr_token(entry_token) is None
    assert decode_entry_qr_token(exit_token) is None

    assert decode_entry_qr_token(entry_token) is not None
    assert decode_exit_qr_token(exit_token) is not None


def test_decode_exit_qr_token_rejects_expired_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    now = datetime.now(timezone.utc)

    payload = {
        "sub": "10",
	"parked_vehicle_id": 777,
        "plate": "ABC123",
        "parking_lot_id": "tornavias",
        "purpose": EXIT_QR_PURPOSE,
        "jti": "expired-exit-test",
        "iat": now - timedelta(minutes=10),
        "exp": now - timedelta(minutes=5),
    }

    token = jwt.encode(
        payload,
        TEST_SECRET,
        algorithm=ALGORITHM,
    )

    assert decode_exit_qr_token(token) is None