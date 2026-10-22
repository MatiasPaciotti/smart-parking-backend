from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.routes.parking_lots as parking_lots_routes
from app.api.dependencies import (
    CurrentGuardiaForParkingLot,
    get_current_user,
)
from app.main import create_app

ADMIN_USER = {
    "id": 10,
    "email": "guardia@unsam.edu.ar",
    "role": "admin",
    "parking_lot_id": None,
}


def create_client(user=None):
    application = create_app()

    if user is not None:
        application.dependency_overrides[get_current_user] = lambda: user

    return TestClient(application)


def test_admin_can_select_tornavias(monkeypatch):
    monkeypatch.setattr(
        parking_lots_routes,
        "create_access_token",
        lambda **kwargs: f"token-{kwargs['parking_lot_id']}",
    )
    client = create_client(ADMIN_USER)

    response = client.post(
        "/api/v1/parking-lots/select",
        json={"parking_lot_id": "tornavias"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "token-tornavias"
    assert data["parking_lot"]["id"] == "tornavias"


def test_admin_can_select_rodriguez_pena(monkeypatch):
    monkeypatch.setattr(
        parking_lots_routes,
        "create_access_token",
        lambda **kwargs: f"token-{kwargs['parking_lot_id']}",
    )
    client = create_client(ADMIN_USER)

    response = client.post(
        "/api/v1/parking-lots/select",
        json={"parking_lot_id": "rodriguez-pena"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "token-rodriguez-pena"
    assert data["parking_lot"]["id"] == "rodriguez-pena"


def test_selection_rejects_unknown_parking_lot():
    client = create_client(ADMIN_USER)

    response = client.post(
        "/api/v1/parking-lots/select",
        json={"parking_lot_id": "garita-inexistente"},
    )

    assert response.status_code == 404


def test_non_admin_cannot_select_parking_lot():
    student = {
        **ADMIN_USER,
        "role": "student",
    }
    client = create_client(student)

    response = client.post(
        "/api/v1/parking-lots/select",
        json={"parking_lot_id": "tornavias"},
    )

    assert response.status_code == 403


def test_selection_requires_authentication():
    client = create_client()

    response = client.post(
        "/api/v1/parking-lots/select",
        json={"parking_lot_id": "tornavias"},
    )

    assert response.status_code == 401


def test_access_token_contains_selected_parking_lot(monkeypatch):
    from app.security.tokens import decode_access_token

    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "test-only-secret-for-hu10-key-at-least-32-bytes",
    )

    client = create_client(ADMIN_USER)

    response = client.post(
        "/api/v1/parking-lots/select",
        json={"parking_lot_id": "tornavias"},
    )

    assert response.status_code == 200

    token = response.json()["access_token"]
    payload = decode_access_token(token)

    assert payload is not None
    assert payload["parking_lot_id"] == "tornavias"
    assert payload["role"] == "admin"


def test_authenticated_user_receives_selected_parking_lot(monkeypatch):
    from app.security.tokens import decode_access_token

    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "test-only-secret-for-hu10-key-at-least-32-bytes",
    )

    selection_client = create_client(ADMIN_USER)
    selection_response = selection_client.post(
        "/api/v1/parking-lots/select",
        json={"parking_lot_id": "tornavias"},
    )

    assert selection_response.status_code == 200
    token = selection_response.json()["access_token"]
    assert decode_access_token(token)["parking_lot_id"] == "tornavias"

    # Usar el token en una nueva petición sin reemplazar la autenticación real.
    authenticated_client = create_client()
    response = authenticated_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["parking_lot_id"] == "tornavias"


def test_admin_can_get_active_parking_lot():
    user = {
        **ADMIN_USER,
        "parking_lot_id": "tornavias",
    }
    client = create_client(user)

    response = client.get("/api/v1/parking-lots/active")

    assert response.status_code == 200
    assert response.json()["parking_lot"]["id"] == "tornavias"


def test_active_parking_lot_requires_selection():
    client = create_client(ADMIN_USER)

    response = client.get("/api/v1/parking-lots/active")

    assert response.status_code == 409


def test_non_admin_cannot_get_active_parking_lot():
    user = {
        **ADMIN_USER,
        "role": "student",
        "parking_lot_id": "tornavias",
    }
    client = create_client(user)

    response = client.get("/api/v1/parking-lots/active")

    assert response.status_code == 403


def test_active_parking_lot_rejects_invalid_selection():
    user = {
        **ADMIN_USER,
        "parking_lot_id": "garita-inexistente",
    }
    client = create_client(user)

    response = client.get("/api/v1/parking-lots/active")

    assert response.status_code == 409


def create_operational_test_client(user):
    application = FastAPI()

    @application.post("/parking-lots/{parking_lot_id}/entry")
    def fake_entry(
        parking_lot_id: str,
        current_guardia: CurrentGuardiaForParkingLot,
    ):
        return {
            "parking_lot_id": parking_lot_id,
            "active_parking_lot_id": current_guardia["parking_lot_id"],
        }

    application.dependency_overrides[get_current_user] = lambda: user

    return TestClient(application)


def test_operational_request_allows_only_selected_parking_lot():
    user = {
        **ADMIN_USER,
        "parking_lot_id": "tornavias",
    }
    client = create_operational_test_client(user)

    allowed_response = client.post("/parking-lots/tornavias/entry")
    rejected_response = client.post("/parking-lots/rodriguez-pena/entry")

    assert allowed_response.status_code == 200
    assert allowed_response.json()["active_parking_lot_id"] == "tornavias"
    assert rejected_response.status_code == 409


def test_operational_request_requires_selected_parking_lot():
    client = create_operational_test_client(ADMIN_USER)

    response = client.post("/parking-lots/tornavias/entry")

    assert response.status_code == 409


def test_operational_request_requires_admin_role():
    user = {
        **ADMIN_USER,
        "role": "student",
        "parking_lot_id": "tornavias",
    }
    client = create_operational_test_client(user)

    response = client.post("/parking-lots/tornavias/entry")

    assert response.status_code == 403


def test_entry_rejects_parking_lot_other_than_active():
    user = {
        **ADMIN_USER,
        "parking_lot_id": "tornavias",
    }
    client = create_client(user)

    response = client.post("/api/v1/parking-lots/rodriguez-pena/entry")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "La garita solicitada no coincide con la garita activa"
    )


def test_exit_rejects_parking_lot_other_than_active():
    user = {
        **ADMIN_USER,
        "parking_lot_id": "tornavias",
    }
    client = create_client(user)

    response = client.post("/api/v1/parking-lots/rodriguez-pena/exit")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "La garita solicitada no coincide con la garita activa"
    )


def test_occupancy_rejects_parking_lot_other_than_active():
    user = {
        **ADMIN_USER,
        "parking_lot_id": "tornavias",
    }
    client = create_client(user)

    response = client.get(
        "/api/v1/parking-lots/rodriguez-pena/occupancy"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "La garita solicitada no coincide con la garita activa"
    )