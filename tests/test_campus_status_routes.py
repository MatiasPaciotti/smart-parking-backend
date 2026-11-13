import psycopg
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import protected as protected_routes
from app.main import create_app

TEST_USER = {
    "id": 10,
    "email": "usuario@unsam.edu.ar",
    "role": "user",
}


def create_client(user=None):
    application = create_app()

    if user is not None:
        application.dependency_overrides[get_current_user] = lambda: user

    return TestClient(application)


def test_campus_status_requires_authentication():
    client = create_client()

    response = client.get("/api/v1/auth/campus-status")

    assert response.status_code == 401


@pytest.mark.parametrize("is_on_campus", [True, False])
def test_authenticated_user_can_get_campus_status(
    monkeypatch,
    is_on_campus,
):
    def fake_get_campus_status(user_id):
        assert user_id == TEST_USER["id"]

        return {
            "account_status": "active",
            "is_on_campus": is_on_campus,
        }

    monkeypatch.setattr(
        protected_routes,
        "get_campus_status_by_user_id",
        fake_get_campus_status,
    )

    client = create_client(TEST_USER)

    response = client.get("/api/v1/auth/campus-status")

    assert response.status_code == 200
    assert response.json() == {
        "is_on_campus": is_on_campus,
    }


def test_campus_status_returns_404_when_user_does_not_exist(
    monkeypatch,
):
    monkeypatch.setattr(
        protected_routes,
        "get_campus_status_by_user_id",
        lambda user_id: None,
    )

    client = create_client(TEST_USER)

    response = client.get("/api/v1/auth/campus-status")

    assert response.status_code == 404
    assert response.json()["detail"] == "No se encontró el usuario"


def test_campus_status_returns_403_when_account_is_inactive(
    monkeypatch,
):
    monkeypatch.setattr(
        protected_routes,
        "get_campus_status_by_user_id",
        lambda user_id: {
            "account_status": "inactive",
            "is_on_campus": False,
        },
    )

    client = create_client(TEST_USER)

    response = client.get("/api/v1/auth/campus-status")

    assert response.status_code == 403
    assert response.json()["detail"] == "La cuenta no está activa"


def test_campus_status_returns_503_when_database_fails(
    monkeypatch,
):
    def fake_get_campus_status(user_id):
        raise psycopg.OperationalError("Database unavailable")

    monkeypatch.setattr(
        protected_routes,
        "get_campus_status_by_user_id",
        fake_get_campus_status,
    )

    client = create_client(TEST_USER)

    response = client.get("/api/v1/auth/campus-status")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "No se pudo consultar el estado del campus"
    )