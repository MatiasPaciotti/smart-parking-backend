import pytest
from fastapi.testclient import TestClient

import app.api.routes.occupancy as occupancy_routes
import app.api.routes.parking_movements as parking_movements_routes
from app.api.dependencies import get_current_user
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


@pytest.mark.parametrize(
    ("parking_lot_id", "parking_lot_name"),
    [
        ("tornavias", "Tornavías"),
        ("rodriguez-pena", "Rodríguez Peña"),
    ],
)
def test_occupancy_is_public_for_both_parking_lots(
    monkeypatch,
    parking_lot_id,
    parking_lot_name,
):
    occupancy_data = {
        "parking_lot": {
            "id": parking_lot_id,
            "name": parking_lot_name,
        },
        "capacity": 100,
        "occupied": 25,
        "available": 75,
        "occupancy_percentage": 25.0,
        "traffic_light": "green",
    }

    monkeypatch.setattr(
        occupancy_routes,
        "get_parking_occupancy",
        lambda requested_id: (
            occupancy_data if requested_id == parking_lot_id else None
        ),
    )

    # No se proporciona usuario ni token.
    client = create_client()
    response = client.get(
        f"/api/v1/parking-lots/{parking_lot_id}/occupancy"
    )

    assert response.status_code == 200
    assert response.json() == occupancy_data


def test_occupancy_returns_404_for_unknown_parking_lot(monkeypatch):
    monkeypatch.setattr(
        occupancy_routes,
        "get_parking_occupancy",
        lambda parking_lot_id: None,
    )

    client = create_client()
    response = client.get(
        "/api/v1/parking-lots/garita-inexistente/occupancy"
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/parking-lots/tornavias/entry",
        "/api/v1/parking-lots/tornavias/exit",
    ],
)
def test_movements_require_authentication(path):
    client = create_client()

    response = client.post(path)

    assert response.status_code == 401


def test_entry_does_not_require_selected_parking_lot(monkeypatch):
    calls = []

    def fake_register_entry(user_id, parking_lot_id):
        calls.append(
            {
                "user_id": user_id,
                "parking_lot_id": parking_lot_id,
            }
        )
        return {
            "parking_lot_id": parking_lot_id,
            "event_type": "entry",
            "occupied": 1,
            "capacity": 100,
        }

    monkeypatch.setattr(
        parking_movements_routes,
        "register_entry",
        fake_register_entry,
    )

    client = create_client(TEST_USER)
    response = client.post(
        "/api/v1/parking-lots/tornavias/entry"
    )

    assert response.status_code == 200
    assert response.json()["event_type"] == "entry"
    assert calls == [
        {
            "user_id": TEST_USER["id"],
            "parking_lot_id": "tornavias",
        }
    ]


def test_exit_does_not_require_selected_parking_lot(monkeypatch):
    calls = []

    def fake_register_exit(user_id, parking_lot_id):
        calls.append(
            {
                "user_id": user_id,
                "parking_lot_id": parking_lot_id,
            }
        )
        return {
            "parking_lot_id": parking_lot_id,
            "event_type": "exit",
            "occupied": 0,
            "capacity": 100,
        }

    monkeypatch.setattr(
        parking_movements_routes,
        "register_exit",
        fake_register_exit,
    )

    client = create_client(TEST_USER)
    response = client.post(
        "/api/v1/parking-lots/tornavias/exit"
    )

    assert response.status_code == 200
    assert response.json()["event_type"] == "exit"
    assert calls == [
        {
            "user_id": TEST_USER["id"],
            "parking_lot_id": "tornavias",
        }
    ]