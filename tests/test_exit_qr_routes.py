from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import entry_qr as entry_qr_routes
from app.main import create_app
from app.services.exit_qr_service import (
    ExitQrInvalidToken,
    ExitQrMovementConflict,
    ExitQrNoActiveVehicle,
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


def test_generate_exit_qr_requires_authentication():
    client = create_client()

    response = client.post("/api/v1/parking-lots/exit/qr")

    assert response.status_code == 401


def test_authenticated_user_can_generate_exit_qr(monkeypatch):
    def fake_request_exit_qr(user_id):
        assert user_id == TEST_USER["id"]

        return {
            "message": "QR de salida generado correctamente",
            "qr_token": "test-exit-qr-token",
            "plate": "ABC123",
            "parking_lot": {
                "id": "tornavias",
                "name": "Tornavías",
            },
            "expires_at": "2026-11-05T18:08:00-03:00",
            "expires_in_seconds": 300,
        }

    monkeypatch.setattr(
        entry_qr_routes,
        "request_exit_qr",
        fake_request_exit_qr,
    )

    client = create_client(TEST_USER)

    response = client.post("/api/v1/parking-lots/exit/qr")

    assert response.status_code == 200
    assert response.json()["qr_token"] == "test-exit-qr-token"
    assert response.json()["plate"] == "ABC123"


def test_generate_exit_qr_returns_409_without_active_vehicle(monkeypatch):
    def fake_request_exit_qr(user_id):
        raise ExitQrNoActiveVehicle(
            "No registrás un ingreso activo en el campus"
        )

    monkeypatch.setattr(
        entry_qr_routes,
        "request_exit_qr",
        fake_request_exit_qr,
    )

    client = create_client(TEST_USER)

    response = client.post("/api/v1/parking-lots/exit/qr")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "No registrás un ingreso activo en el campus"
    )


def test_scan_exit_qr_requires_authentication():
    client = create_client()

    response = client.post(
        "/api/v1/parking-lots/exit/qr/scan",
        json={"qr_token": "test-exit-qr-token"},
    )

    assert response.status_code == 401


def test_non_admin_cannot_scan_exit_qr(monkeypatch):
    scan_calls = []

    monkeypatch.setattr(
        entry_qr_routes,
        "process_exit_qr_scan",
        lambda token: scan_calls.append(token),
    )

    client = create_client(TEST_USER)

    response = client.post(
        "/api/v1/parking-lots/exit/qr/scan",
        json={"qr_token": "test-exit-qr-token"},
    )

    assert response.status_code == 403
    assert scan_calls == []


def test_admin_can_scan_valid_exit_qr(monkeypatch):
    def fake_scan_exit_qr(token):
        assert token == "test-exit-qr-token"

        return {
            "message": "Egreso registrado correctamente",
            "plate": "ABC123",
            "parking_lot_id": "tornavias",
            "event_type": "exit",
            "occupied": 10,
            "capacity": 280,
        }

    monkeypatch.setattr(
        entry_qr_routes,
        "process_exit_qr_scan",
        fake_scan_exit_qr,
    )

    client = create_client(TEST_ADMIN)

    response = client.post(
        "/api/v1/parking-lots/exit/qr/scan",
        json={"qr_token": "test-exit-qr-token"},
    )

    assert response.status_code == 200
    assert response.json()["plate"] == "ABC123"
    assert response.json()["event_type"] == "exit"
    assert response.json()["occupied"] == 10
    assert response.json()["capacity"] == 280


def test_admin_scan_rejects_invalid_exit_qr(monkeypatch):
    def fake_scan_exit_qr(token):
        raise ExitQrInvalidToken("El QR es inválido o está vencido")

    monkeypatch.setattr(
        entry_qr_routes,
        "process_exit_qr_scan",
        fake_scan_exit_qr,
    )

    client = create_client(TEST_ADMIN)

    response = client.post(
        "/api/v1/parking-lots/exit/qr/scan",
        json={"qr_token": "invalid-token"},
    )

    assert response.status_code == 400


def test_admin_scan_rejects_exit_movement_conflict(monkeypatch):
    def fake_scan_exit_qr(token):
        raise ExitQrMovementConflict(
            "El vehículo ya no tiene un ingreso activo"
        )

    monkeypatch.setattr(
        entry_qr_routes,
        "process_exit_qr_scan",
        fake_scan_exit_qr,
    )

    client = create_client(TEST_ADMIN)

    response = client.post(
        "/api/v1/parking-lots/exit/qr/scan",
        json={"qr_token": "test-exit-qr-token"},
    )

    assert response.status_code == 409