from datetime import datetime, timedelta, timezone

import pytest

from app.services import entry_qr_service as service

TEST_PROFILE = {
    "id": 10,
    "full_name": "Usuario de prueba",
    "email": "usuario@unsam.edu.ar",
    "role": "user",
    "account_status": "active",
    "plate": "ABC123",
    "dni": "12345678",
    "email_verified": True,
    "profile_complete": True,
}


def configure_valid_request(monkeypatch, available=10):
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    generated_tokens = []

    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: TEST_PROFILE,
    )

    monkeypatch.setattr(
        service,
        "has_active_vehicle",
        lambda user_id: False,
    )

    monkeypatch.setattr(
        service,
        "get_parking_occupancy",
        lambda parking_lot_id: {
            "parking_lot": {
                "id": parking_lot_id,
                "name": "Tornavías",
            },
            "capacity": 100,
            "occupied": 90,
            "available": available,
            "occupancy_percentage": 90.0,
            "traffic_light": "yellow",
        },
    )

    def fake_create_token(user_id, plate, parking_lot_id):
        generated_tokens.append({
            "user_id": user_id,
            "plate": plate,
            "parking_lot_id": parking_lot_id,
        })
        return "test-qr-token", expires_at

    monkeypatch.setattr(
        service,
        "create_entry_qr_token",
        fake_create_token,
    )

    return generated_tokens, expires_at


def test_request_entry_qr_success(monkeypatch):
    generated_tokens, expires_at = configure_valid_request(monkeypatch)

    result = service.request_entry_qr(
        user_id=10,
        parking_lot_id="tornavias",
    )

    assert result["message"] == "QR de entrada generado correctamente"
    assert result["qr_token"] == "test-qr-token"
    assert result["plate"] == "ABC123"
    assert result["parking_lot"]["id"] == "tornavias"
    assert result["expires_at"] == expires_at.isoformat()
    assert result["expires_in_seconds"] == 300

    assert generated_tokens == [
        {
            "user_id": 10,
            "plate": "ABC123",
            "parking_lot_id": "tornavias",
        }
    ]


def test_request_entry_qr_rejects_unknown_user(monkeypatch):
    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: None,
    )

    with pytest.raises(service.EntryQrUserNotFound):
        service.request_entry_qr(10, "tornavias")


def test_request_entry_qr_rejects_inactive_account(monkeypatch):
    profile = {
        **TEST_PROFILE,
        "account_status": "inactive",
    }

    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: profile,
    )

    with pytest.raises(service.EntryQrUserInactive):
        service.request_entry_qr(10, "tornavias")


def test_request_entry_qr_rejects_missing_plate(monkeypatch):
    profile = {
        **TEST_PROFILE,
        "plate": None,
    }

    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: profile,
    )

    with pytest.raises(service.EntryQrProfileIncomplete):
        service.request_entry_qr(10, "tornavias")


def test_request_entry_qr_rejects_user_already_inside(monkeypatch):
    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: TEST_PROFILE,
    )

    monkeypatch.setattr(
        service,
        "has_active_vehicle",
        lambda user_id: True,
    )

    with pytest.raises(service.EntryQrUserAlreadyInside):
        service.request_entry_qr(10, "tornavias")


def test_request_entry_qr_rejects_unknown_parking_lot(monkeypatch):
    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: TEST_PROFILE,
    )

    monkeypatch.setattr(
        service,
        "has_active_vehicle",
        lambda user_id: False,
    )

    monkeypatch.setattr(
        service,
        "get_parking_occupancy",
        lambda parking_lot_id: None,
    )

    with pytest.raises(service.EntryQrParkingLotNotFound):
        service.request_entry_qr(10, "inexistente")


def test_request_entry_qr_rejects_full_parking_lot(monkeypatch):
    generated_tokens, _ = configure_valid_request(
        monkeypatch,
        available=0,
    )

    with pytest.raises(service.EntryQrParkingLotFull):
        service.request_entry_qr(10, "tornavias")

    assert generated_tokens == []


QR_PAYLOAD = {
    "sub": "10",
    "plate": "ABC123",
    "parking_lot_id": "tornavias",
    "purpose": "parking_entry",
    "jti": "test-entry-qr-001",
    "iat": 1000000,
    "exp": 1000300,
}


def test_scan_entry_qr_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr(
        service,
        "decode_entry_qr_token",
        lambda token: None,
    )

    with pytest.raises(service.EntryQrInvalidToken):
        service.scan_entry_qr("invalid-token")


def test_scan_entry_qr_rejects_unknown_user(monkeypatch):
    monkeypatch.setattr(
        service,
        "decode_entry_qr_token",
        lambda token: QR_PAYLOAD,
    )
    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: None,
    )

    with pytest.raises(service.EntryQrUserNotFound):
        service.scan_entry_qr("valid-token")


def test_scan_entry_qr_rejects_inactive_account(monkeypatch):
    profile = {
        **TEST_PROFILE,
        "account_status": "inactive",
    }

    monkeypatch.setattr(
        service,
        "decode_entry_qr_token",
        lambda token: QR_PAYLOAD,
    )
    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: profile,
    )

    with pytest.raises(service.EntryQrUserInactive):
        service.scan_entry_qr("valid-token")


def test_scan_entry_qr_rejects_changed_plate(monkeypatch):
    profile = {
        **TEST_PROFILE,
        "plate": "XYZ789",
    }

    monkeypatch.setattr(
        service,
        "decode_entry_qr_token",
        lambda token: QR_PAYLOAD,
    )
    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: profile,
    )

    with pytest.raises(service.EntryQrInvalidToken):
        service.scan_entry_qr("valid-token")


def test_scan_entry_qr_registers_entry(monkeypatch):
    monkeypatch.setattr(
        service,
        "decode_entry_qr_token",
        lambda token: QR_PAYLOAD,
    )
    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: TEST_PROFILE,
    )
    monkeypatch.setattr(
        service,
        "register_entry",
        lambda user_id, parking_lot_id: {
            "parking_lot_id": parking_lot_id,
            "event_type": "entry",
            "occupied": 11,
            "capacity": 280,
        },
    )

    result = service.scan_entry_qr("valid-token")

    assert result["message"] == "Ingreso registrado correctamente"
    assert result["full_name"] == "Usuario de prueba"
    assert result["plate"] == "ABC123"
    assert result["parking_lot_id"] == "tornavias"
    assert result["event_type"] == "entry"
    assert result["occupied"] == 11


def test_scan_entry_qr_rejects_duplicate_entry(monkeypatch):
    monkeypatch.setattr(
        service,
        "decode_entry_qr_token",
        lambda token: QR_PAYLOAD,
    )
    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: TEST_PROFILE,
    )

    def fake_register_entry(user_id, parking_lot_id):
        raise service.ParkingMovementConflict(
            "El usuario ya tiene un vehículo estacionado"
        )

    monkeypatch.setattr(
        service,
        "register_entry",
        fake_register_entry,
    )

    with pytest.raises(service.EntryQrMovementConflict):
        service.scan_entry_qr("valid-token")


def test_scan_entry_qr_rejects_unknown_parking_lot(monkeypatch):
    monkeypatch.setattr(
        service,
        "decode_entry_qr_token",
        lambda token: QR_PAYLOAD,
    )
    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: TEST_PROFILE,
    )

    def fake_register_entry(user_id, parking_lot_id):
        raise service.ParkingLotNotFound(
            "El estacionamiento solicitado no existe"
        )

    monkeypatch.setattr(
        service,
        "register_entry",
        fake_register_entry,
    )

    with pytest.raises(service.EntryQrParkingLotNotFound):
        service.scan_entry_qr("valid-token")


@pytest.mark.parametrize(
    "profile_changes",
    [
        {"email_verified": False},
        {"email": "usuario@gmail.com"},
        {"role": "admin"},
    ],
    ids=[
        "email-not-verified",
        "non-institutional-email",
        "admin-role",
    ],
)
def test_request_entry_qr_rejects_ineligible_user(
    monkeypatch,
    profile_changes,
):
    profile = {
        **TEST_PROFILE,
        **profile_changes,
    }

    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: profile,
    )

    with pytest.raises(service.EntryQrUserNotEligible):
        service.request_entry_qr(10, "tornavias")


@pytest.mark.parametrize(
    "profile_changes",
    [
        {"email_verified": False},
        {"email": "usuario@gmail.com"},
        {"role": "admin"},
    ],
    ids=[
        "email-not-verified",
        "non-institutional-email",
        "admin-role",
    ],
)
def test_scan_entry_qr_rejects_ineligible_user(
    monkeypatch,
    profile_changes,
):
    profile = {
        **TEST_PROFILE,
        **profile_changes,
    }

    monkeypatch.setattr(
        service,
        "decode_entry_qr_token",
        lambda token: QR_PAYLOAD,
    )

    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: profile,
    )

    with pytest.raises(service.EntryQrUserNotEligible):
        service.scan_entry_qr("valid-token")