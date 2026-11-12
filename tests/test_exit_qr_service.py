from datetime import datetime, timedelta, timezone

import pytest

from app.services import exit_qr_service as service

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

ACTIVE_VEHICLE = {
    "parked_vehicle_id": 777,
    "parking_lot_id": "tornavias",
    "parking_lot": {
        "id": "tornavias",
        "name": "Tornavías",
    },
}

EXIT_PAYLOAD = {
    "sub": "10",
    "plate": "ABC123",
    "parking_lot_id": "tornavias",
    "purpose": "parking_exit",
    "jti": "test-exit-qr-001",
    "parked_vehicle_id": 777,
    "iat": 1000000,
    "exp": 1000300,
}


def configure_valid_exit_request(monkeypatch):
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    generated_tokens = []

    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: TEST_PROFILE,
    )

    monkeypatch.setattr(
        service,
        "get_active_vehicle",
        lambda user_id: ACTIVE_VEHICLE,
    )

    def fake_create_token(
        user_id,
        plate,
        parking_lot_id,
        parked_vehicle_id,
    ):
        generated_tokens.append({
            "user_id": user_id,
            "plate": plate,
            "parking_lot_id": parking_lot_id,
            "parked_vehicle_id": parked_vehicle_id,
        })
        return "test-exit-token", expires_at

    monkeypatch.setattr(
        service,
        "create_exit_qr_token",
        fake_create_token,
    )

    return generated_tokens, expires_at


def test_request_exit_qr_success(monkeypatch):
    generated_tokens, expires_at = configure_valid_exit_request(monkeypatch)

    result = service.request_exit_qr(user_id=10)

    assert result["message"] == "QR de salida generado correctamente"
    assert result["qr_token"] == "test-exit-token"
    assert result["plate"] == "ABC123"
    assert result["parking_lot"]["id"] == "tornavias"
    assert result["expires_at"] == expires_at.isoformat()
    assert result["expires_in_seconds"] == 300

    assert generated_tokens == [
        {
            "user_id": 10,
            "plate": "ABC123",
            "parking_lot_id": "tornavias",
            "parked_vehicle_id": 777,
        }
    ]


def test_request_exit_qr_rejects_unknown_user(monkeypatch):
    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: None,
    )

    with pytest.raises(service.ExitQrUserNotFound):
        service.request_exit_qr(10)


def test_request_exit_qr_rejects_inactive_account(monkeypatch):
    profile = {
        **TEST_PROFILE,
        "account_status": "inactive",
    }

    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: profile,
    )

    with pytest.raises(service.ExitQrUserInactive):
        service.request_exit_qr(10)


def test_request_exit_qr_rejects_missing_plate(monkeypatch):
    profile = {
        **TEST_PROFILE,
        "plate": None,
    }

    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: profile,
    )

    with pytest.raises(service.ExitQrProfileIncomplete):
        service.request_exit_qr(10)


def test_request_exit_qr_rejects_user_without_active_vehicle(
    monkeypatch,
):
    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: TEST_PROFILE,
    )

    monkeypatch.setattr(
        service,
        "get_active_vehicle",
        lambda user_id: None,
    )

    with pytest.raises(service.ExitQrNoActiveVehicle):
        service.request_exit_qr(10)


def test_scan_exit_qr_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr(
        service,
        "decode_exit_qr_token",
        lambda token: None,
    )

    with pytest.raises(service.ExitQrInvalidToken):
        service.scan_exit_qr("invalid-token")


def test_scan_exit_qr_registers_exit(monkeypatch):
    monkeypatch.setattr(
        service,
        "decode_exit_qr_token",
        lambda token: EXIT_PAYLOAD,
    )

    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: TEST_PROFILE,
    )

    monkeypatch.setattr(
        service,
        "get_active_vehicle",
        lambda user_id: ACTIVE_VEHICLE,
    )

    calls = []

    def fake_register_exit(
        user_id,
        parking_lot_id,
        expected_parked_vehicle_id,
    ):
        calls.append({
            "user_id": user_id,
            "parking_lot_id": parking_lot_id,
            "expected_parked_vehicle_id": expected_parked_vehicle_id,
        })

        return {
            "parking_lot_id": parking_lot_id,
            "event_type": "exit",
            "occupied": 9,
            "capacity": 280,
        }

    monkeypatch.setattr(
        service,
        "register_exit",
        fake_register_exit,
    )

    result = service.scan_exit_qr("valid-token")

    assert result["message"] == "Egreso registrado correctamente"
    assert result["plate"] == "ABC123"
    assert result["event_type"] == "exit"
    assert result["occupied"] == 9
    assert result["full_name"] == "Usuario de prueba"
    assert result["parking_lot"] == ACTIVE_VEHICLE["parking_lot"]
    assert result["capacity"] == 280
    assert result["available"] == 271
    assert result["occupancy_percentage"] == 3.2
    assert result["registered_at"].endswith("+00:00")

    assert calls == [
        {
            "user_id": 10,
            "parking_lot_id": "tornavias",
            "expected_parked_vehicle_id": 777,
        }
    ]


@pytest.mark.parametrize(
    ("active_vehicle", "expected_error"),
    [
        (
            None,
            service.ExitQrNoActiveVehicle,
        ),
        (
            {
                **ACTIVE_VEHICLE,
                "parked_vehicle_id": 812,
            },
            service.ExitQrInvalidToken,
        ),
        (
            {
                **ACTIVE_VEHICLE,
                "parking_lot_id": "rodriguez-pena",
            },
            service.ExitQrInvalidToken,
        ),
    ],
)
def test_scan_exit_qr_rejects_different_active_vehicle(
    monkeypatch,
    active_vehicle,
    expected_error,
):
    monkeypatch.setattr(
        service,
        "decode_exit_qr_token",
        lambda token: EXIT_PAYLOAD,
    )

    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: TEST_PROFILE,
    )

    monkeypatch.setattr(
        service,
        "get_active_vehicle",
        lambda user_id: active_vehicle,
    )

    with pytest.raises(expected_error):
        service.scan_exit_qr("old-token")


def test_scan_exit_qr_rejects_changed_plate(monkeypatch):
    profile = {
        **TEST_PROFILE,
        "plate": "XYZ789",
    }

    monkeypatch.setattr(
        service,
        "decode_exit_qr_token",
        lambda token: EXIT_PAYLOAD,
    )

    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: profile,
    )

    with pytest.raises(service.ExitQrInvalidToken):
        service.scan_exit_qr("valid-token")


def test_scan_exit_qr_rejects_inactive_account(monkeypatch):
    profile = {
        **TEST_PROFILE,
        "account_status": "inactive",
    }

    monkeypatch.setattr(
        service,
        "decode_exit_qr_token",
        lambda token: EXIT_PAYLOAD,
    )

    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: profile,
    )

    with pytest.raises(service.ExitQrUserInactive):
        service.scan_exit_qr("valid-token")


def test_scan_exit_qr_rejects_movement_conflict(monkeypatch):
    from app.repositories.parking_movement_repository import (
        ParkingMovementConflict,
    )

    monkeypatch.setattr(
        service,
        "decode_exit_qr_token",
        lambda token: EXIT_PAYLOAD,
    )

    monkeypatch.setattr(
        service,
        "get_user_profile_by_id",
        lambda user_id: TEST_PROFILE,
    )

    monkeypatch.setattr(
        service,
        "get_active_vehicle",
        lambda user_id: ACTIVE_VEHICLE,
    )

    def fake_register_exit(**kwargs):
        raise ParkingMovementConflict(
            "El usuario no tiene un vehículo estacionado en ese lugar"
        )

    monkeypatch.setattr(
        service,
        "register_exit",
        fake_register_exit,
    )

    with pytest.raises(service.ExitQrMovementConflict):
        service.scan_exit_qr("valid-token")