from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import entry_qr as entry_qr_routes
from app.main import create_app
from app.services.entry_qr_service import (
    EntryQrInvalidToken,
    EntryQrMovementConflict,
    EntryQrParkingLotFull,
)

TEST_USER = {
    "id": 10,
    "email": "usuario@unsam.edu.ar",
    "role": "user",
}

TEST_ADMIN = {
    "id": 20,
    "email": "guardia@unsam.edu.ar",
    "role": "admin",
}


def create_client(user=None):
    application = create_app()

    if user is not None:
        application.dependency_overrides[get_current_user] = lambda: user

    return TestClient(application)


def test_generate_entry_qr_requires_authentication():
    client = create_client()

    response = client.post(
        "/api/v1/parking-lots/tornavias/entry/qr"
    )

    assert response.status_code == 401


def test_authenticated_user_can_generate_entry_qr(monkeypatch):
    def fake_request_entry_qr(user_id, parking_lot_id):
        assert user_id == TEST_USER["id"]
        assert parking_lot_id == "tornavias"

        return {
            "message": "QR de entrada generado correctamente",
            "qr_token": "test-qr-token",
            "plate": "ABC123",
            "parking_lot": {
                "id": "tornavias",
                "name": "Tornavías",
            },
            "expires_at": "2026-11-05T12:05:00+00:00",
            "expires_in_seconds": 300,
        }

    monkeypatch.setattr(
        entry_qr_routes,
        "request_entry_qr",
        fake_request_entry_qr,
    )

    client = create_client(TEST_USER)

    response = client.post(
        "/api/v1/parking-lots/tornavias/entry/qr"
    )

    assert response.status_code == 200
    assert response.json()["qr_token"] == "test-qr-token"
    assert response.json()["plate"] == "ABC123"


def test_generate_entry_qr_returns_409_when_parking_is_full(monkeypatch):
    def fake_request_entry_qr(user_id, parking_lot_id):
        raise EntryQrParkingLotFull("Estacionamiento Completo")

    monkeypatch.setattr(
        entry_qr_routes,
        "request_entry_qr",
        fake_request_entry_qr,
    )

    client = create_client(TEST_USER)

    response = client.post(
        "/api/v1/parking-lots/tornavias/entry/qr"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Estacionamiento Completo"


def test_scan_entry_qr_requires_authentication():
    client = create_client()

    response = client.post(
        "/api/v1/parking-lots/entry/qr/scan",
        json={"qr_token": "test-qr-token"},
    )

    assert response.status_code == 401


def test_non_admin_cannot_scan_entry_qr(monkeypatch):
    scan_calls = []

    monkeypatch.setattr(
        entry_qr_routes,
        "process_entry_qr_scan",
        lambda token: scan_calls.append(token),
    )

    client = create_client(TEST_USER)

    response = client.post(
        "/api/v1/parking-lots/entry/qr/scan",
        json={"qr_token": "test-qr-token"},
    )

    assert response.status_code == 403
    assert scan_calls == []


def test_admin_can_scan_valid_entry_qr(monkeypatch):
    def fake_scan_entry_qr(token):
        assert token == "test-qr-token"

        return {
            "message": "Ingreso registrado correctamente",
            "parking_lot_id": "tornavias",
            "event_type": "entry",
            "occupied": 11,
            "capacity": 280,
            "plate": "ABC123",
        }

    monkeypatch.setattr(
        entry_qr_routes,
        "process_entry_qr_scan",
        fake_scan_entry_qr,
    )

    client = create_client(TEST_ADMIN)

    response = client.post(
        "/api/v1/parking-lots/entry/qr/scan",
        json={"qr_token": "test-qr-token"},
    )

    assert response.status_code == 200
    assert response.json()["event_type"] == "entry"
    assert response.json()["plate"] == "ABC123"


def test_admin_scan_rejects_invalid_qr(monkeypatch):
    def fake_scan_entry_qr(token):
        raise EntryQrInvalidToken("El QR es inválido o está vencido")

    monkeypatch.setattr(
        entry_qr_routes,
        "process_entry_qr_scan",
        fake_scan_entry_qr,
    )

    client = create_client(TEST_ADMIN)

    response = client.post(
        "/api/v1/parking-lots/entry/qr/scan",
        json={"qr_token": "invalid-token"},
    )

    assert response.status_code == 400


def test_admin_scan_rejects_duplicate_entry(monkeypatch):
    def fake_scan_entry_qr(token):
        raise EntryQrMovementConflict(
            "El usuario ya tiene un vehículo estacionado"
        )

    monkeypatch.setattr(
        entry_qr_routes,
        "process_entry_qr_scan",
        fake_scan_entry_qr,
    )

    client = create_client(TEST_ADMIN)

    response = client.post(
        "/api/v1/parking-lots/entry/qr/scan",
        json={"qr_token": "test-qr-token"},
    )

    assert response.status_code == 409