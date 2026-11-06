import pytest
from fastapi.testclient import TestClient
from psycopg import errors

from app.api.dependencies import get_current_user
from app.api.routes import guests as guest_routes
from app.main import create_app
from app.repositories import guest_repository
from app.repositories.guest_repository import (
    GuestParkingLotNotFound,
    GuestVehicleConflict,
    GuestVehicleNotFound,
    delete_guest_vehicle,
    insert_guest_vehicle,
    select_guest_vehicles,
)

TEST_ADMIN = {
    "id": 20,
    "email": "guardia@unsam.edu.ar",
    "role": "admin",
}

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


def test_guest_routes_require_authentication():
    client = create_client()

    response = client.post(
        "/api/v1/admin/parking-lots/tornavias/guests",
        json={"patente": "ABC123"},
    )

    assert response.status_code == 401


def test_guest_routes_reject_non_admin_users(monkeypatch):
    def fail_if_called(**kwargs):
        raise AssertionError("El servicio no debería ejecutarse para un usuario común")

    monkeypatch.setattr(guest_routes, "register_guest_vehicle", fail_if_called)
    monkeypatch.setattr(guest_routes, "remove_guest_vehicle", fail_if_called)
    client = create_client(TEST_USER)

    post_response = client.post(
        "/api/v1/admin/parking-lots/tornavias/guests",
        json={"patente": "ABC123"},
    )
    delete_response = client.delete(
        "/api/v1/admin/parking-lots/tornavias/guests/ABC123",
    )

    assert post_response.status_code == 403
    assert delete_response.status_code == 403


def test_admin_registers_guest_vehicle_with_normalized_plate(monkeypatch):
    def fake_register_guest_vehicle(plate, created_by, parking_lot_id):
        assert plate == "ABC123"
        assert created_by == TEST_ADMIN["id"]
        assert parking_lot_id == "tornavias"

        return {
            "parking_lot_id": "tornavias",
            "patente": "ABC123",
            "occupied": 5,
            "capacity": 10,
        }

    monkeypatch.setattr(
        guest_routes,
        "register_guest_vehicle",
        fake_register_guest_vehicle,
    )
    client = create_client(TEST_ADMIN)

    response = client.post(
        "/api/v1/admin/parking-lots/tornavias/guests",
        json={"patente": " abc 123 "},
    )

    assert response.status_code == 201
    assert response.json()["message"] == "Vehículo de invitado registrado correctamente"
    assert response.json()["occupied"] == 5


def test_register_guest_rejects_invalid_plate():
    client = create_client(TEST_ADMIN)

    response = client.post(
        "/api/v1/admin/parking-lots/tornavias/guests",
        json={"patente": "XYZ"},
    )

    assert response.status_code == 422


def test_register_guest_returns_404_when_parking_lot_does_not_exist(monkeypatch):
    def fake_register_guest_vehicle(**kwargs):
        raise GuestParkingLotNotFound("El estacionamiento solicitado no existe")

    monkeypatch.setattr(
        guest_routes,
        "register_guest_vehicle",
        fake_register_guest_vehicle,
    )
    client = create_client(TEST_ADMIN)

    response = client.post(
        "/api/v1/admin/parking-lots/inexistente/guests",
        json={"patente": "ABC123"},
    )

    assert response.status_code == 404


def test_register_guest_returns_409_on_conflict(monkeypatch):
    def fake_register_guest_vehicle(**kwargs):
        raise GuestVehicleConflict("El estacionamiento no tiene lugares disponibles")

    monkeypatch.setattr(
        guest_routes,
        "register_guest_vehicle",
        fake_register_guest_vehicle,
    )
    client = create_client(TEST_ADMIN)

    response = client.post(
        "/api/v1/admin/parking-lots/tornavias/guests",
        json={"patente": "ABC123"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "El estacionamiento no tiene lugares disponibles"


def test_remove_guest_rejects_invalid_plate_in_path():
    client = create_client(TEST_ADMIN)

    response = client.delete("/api/v1/admin/parking-lots/tornavias/guests/123")

    assert response.status_code == 422


def test_remove_guest_returns_404_when_vehicle_is_not_parked(monkeypatch):
    def fake_remove_guest_vehicle(**kwargs):
        raise GuestVehicleNotFound("El invitado no tiene un vehículo estacionado en ese lugar")

    monkeypatch.setattr(
        guest_routes,
        "remove_guest_vehicle",
        fake_remove_guest_vehicle,
    )
    client = create_client(TEST_ADMIN)

    response = client.delete("/api/v1/admin/parking-lots/tornavias/guests/ABC123")

    assert response.status_code == 404


class FakeResult:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.row


class FakeConnection:
    """Responde según un fragmento del SQL. Cada respuesta es una fila o una excepción."""

    def __init__(self, responses):
        self.responses = responses

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params=None):
        for fragment, outcome in self.responses:
            if fragment in query:
                if isinstance(outcome, Exception):
                    raise outcome

                return FakeResult(outcome)

        raise AssertionError(f"Consulta inesperada: {query}")


def patch_connection(monkeypatch, responses):
    monkeypatch.setattr(
        guest_repository,
        "get_database_connection",
        lambda: FakeConnection(responses),
    )


def unique_violation(constraint_name):
    class FakeDiagnostic:
        pass

    diagnostic = FakeDiagnostic()
    diagnostic.constraint_name = constraint_name

    class FakeUniqueViolation(errors.UniqueViolation):
        @property
        def diag(self):
            return diagnostic

    return FakeUniqueViolation("duplicate key")


def test_insert_guest_vehicle_returns_updated_occupancy(monkeypatch):
    patch_connection(
        monkeypatch,
        [
            ("FROM parking_lots", (10,)),
            ('FROM "user"', None),
            ("INSERT INTO guest", (7,)),
            ("WHERE guest_id", None),
            ("SELECT COUNT(*)", (4,)),
            ("INSERT INTO parked_vehicles", None),
        ],
    )

    result = insert_guest_vehicle("ABC123", TEST_ADMIN["id"], "tornavias")

    assert result == {
        "parking_lot_id": "tornavias",
        "patente": "ABC123",
        "occupied": 5,
        "capacity": 10,
    }


def test_insert_guest_vehicle_rejects_plate_of_registered_user(monkeypatch):
    patch_connection(
        monkeypatch,
        [
            ("FROM parking_lots", (10,)),
            ('FROM "user"', (1,)),
        ],
    )

    with pytest.raises(GuestVehicleConflict):
        insert_guest_vehicle("ABC123", TEST_ADMIN["id"], "tornavias")


def test_insert_guest_vehicle_rejects_when_parking_lot_is_full(monkeypatch):
    patch_connection(
        monkeypatch,
        [
            ("FROM parking_lots", (10,)),
            ('FROM "user"', None),
            ("INSERT INTO guest", (7,)),
            ("WHERE guest_id", None),
            ("SELECT COUNT(*)", (10,)),
        ],
    )

    with pytest.raises(GuestVehicleConflict) as error:
        insert_guest_vehicle("ABC123", TEST_ADMIN["id"], "tornavias")

    assert str(error.value) == "El estacionamiento no tiene lugares disponibles"


def test_insert_guest_vehicle_translates_unique_guest_constraint(monkeypatch):
    patch_connection(
        monkeypatch,
        [
            ("FROM parking_lots", (10,)),
            ('FROM "user"', None),
            ("INSERT INTO guest", (7,)),
            ("WHERE guest_id", None),
            ("SELECT COUNT(*)", (4,)),
            (
                "INSERT INTO parked_vehicles",
                unique_violation("parked_vehicles_guest_id_key"),
            ),
        ],
    )

    with pytest.raises(GuestVehicleConflict):
        insert_guest_vehicle("ABC123", TEST_ADMIN["id"], "tornavias")


def test_insert_guest_vehicle_rejects_unknown_parking_lot():
    with pytest.raises(GuestParkingLotNotFound):
        insert_guest_vehicle("ABC123", TEST_ADMIN["id"], "inexistente")


def test_delete_guest_vehicle_returns_updated_occupancy(monkeypatch):
    patch_connection(
        monkeypatch,
        [
            ("FROM parking_lots", (10,)),
            ("DELETE FROM parked_vehicles", (3,)),
            ("SELECT COUNT(*)", (3,)),
        ],
    )

    result = delete_guest_vehicle("ABC123", "tornavias")

    assert result == {
        "parking_lot_id": "tornavias",
        "patente": "ABC123",
        "occupied": 3,
        "capacity": 10,
    }


def test_delete_guest_vehicle_raises_when_not_parked(monkeypatch):
    patch_connection(
        monkeypatch,
        [
            ("FROM parking_lots", (10,)),
            ("DELETE FROM parked_vehicles", None),
        ],
    )

    with pytest.raises(GuestVehicleNotFound):
        delete_guest_vehicle("ABC123", "tornavias")


def test_admin_lists_parked_guest_vehicles(monkeypatch):
    def fake_list_guest_vehicles(parking_lot_id):
        assert parking_lot_id == "tornavias"

        return [{"patente": "ABC123", "entered_at": "2026-11-06T10:00:00+00:00"}]

    monkeypatch.setattr(
        guest_routes,
        "list_guest_vehicles",
        fake_list_guest_vehicles,
    )
    client = create_client(TEST_ADMIN)

    response = client.get("/api/v1/admin/parking-lots/tornavias/guests")

    assert response.status_code == 200
    assert response.json() == {
        "parking_lot_id": "tornavias",
        "guests": [{"patente": "ABC123", "entered_at": "2026-11-06T10:00:00+00:00"}],
    }


def test_list_guests_rejects_non_admin_users(monkeypatch):
    def fail_if_called(**kwargs):
        raise AssertionError("El servicio no debería ejecutarse para un usuario común")

    monkeypatch.setattr(guest_routes, "list_guest_vehicles", fail_if_called)
    client = create_client(TEST_USER)

    response = client.get("/api/v1/admin/parking-lots/tornavias/guests")

    assert response.status_code == 403


def test_list_guests_returns_404_when_parking_lot_does_not_exist(monkeypatch):
    def fake_list_guest_vehicles(**kwargs):
        raise GuestParkingLotNotFound("El estacionamiento solicitado no existe")

    monkeypatch.setattr(
        guest_routes,
        "list_guest_vehicles",
        fake_list_guest_vehicles,
    )
    client = create_client(TEST_ADMIN)

    response = client.get("/api/v1/admin/parking-lots/inexistente/guests")

    assert response.status_code == 404


def test_select_guest_vehicles_returns_parked_guests(monkeypatch):
    patch_connection(
        monkeypatch,
        [
            ("JOIN guest", [("ABC123", "2026-11-06T10:00:00+00:00")]),
        ],
    )

    result = select_guest_vehicles("tornavias")

    assert result == [
        {"patente": "ABC123", "entered_at": "2026-11-06T10:00:00+00:00"},
    ]


def test_select_guest_vehicles_rejects_unknown_parking_lot():
    with pytest.raises(GuestParkingLotNotFound):
        select_guest_vehicles("inexistente")
