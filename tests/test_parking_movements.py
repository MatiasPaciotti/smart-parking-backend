from psycopg import errors

import pytest
from fastapi import HTTPException

from app.api.routes import parking_movements
from app.repositories.parking_movement_repository import (
    ParkingLotNotFound,
    ParkingMovementConflict,
)


TEST_USER = {
    "id": 999999,
    "email": "test@example.com",
    "role": "user",
}


def test_entry_returns_404_when_parking_lot_does_not_exist(monkeypatch):
    def fake_register_entry(user_id, parking_lot_id):
        raise ParkingLotNotFound("El estacionamiento solicitado no existe")

    monkeypatch.setattr(
        parking_movements,
        "register_entry",
        fake_register_entry,
    )

    with pytest.raises(HTTPException) as error:
        parking_movements.enter_parking_lot(
            "inexistente",
            TEST_USER,
        )

    assert error.value.status_code == 404
    assert error.value.detail == "El estacionamiento solicitado no existe"


def test_entry_returns_409_when_movement_conflicts(monkeypatch):
    def fake_register_entry(user_id, parking_lot_id):
        raise ParkingMovementConflict(
            "El usuario ya tiene un vehículo estacionado"
        )

    monkeypatch.setattr(
        parking_movements,
        "register_entry",
        fake_register_entry,
    )

    with pytest.raises(HTTPException) as error:
        parking_movements.enter_parking_lot(
            "rodriguez-pena",
            TEST_USER,
        )

    assert error.value.status_code == 409


def test_exit_returns_409_when_user_has_no_parked_vehicle(monkeypatch):
    def fake_register_exit(user_id, parking_lot_id):
        raise ParkingMovementConflict(
            "El usuario no tiene un vehículo estacionado en ese lugar"
        )

    monkeypatch.setattr(
        parking_movements,
        "register_exit",
        fake_register_exit,
    )

    with pytest.raises(HTTPException) as error:
        parking_movements.exit_parking_lot(
            "rodriguez-pena",
            TEST_USER,
        )

    assert error.value.status_code == 409


def test_entry_returns_movement_when_successful(monkeypatch):
    monkeypatch.setattr(
        parking_movements,
        "register_entry",
        lambda user_id, parking_lot_id: {
            "parking_lot_id": parking_lot_id,
            "event_type": "entry",
            "occupied": 10,
            "capacity": 280,
        },
    )

    result = parking_movements.enter_parking_lot(
        "rodriguez-pena",
        TEST_USER,
    )

    assert result["message"] == "Ingreso registrado correctamente"
    assert result["event_type"] == "entry"
    assert result["occupied"] == 10


def test_exit_returns_movement_when_successful(monkeypatch):
    monkeypatch.setattr(
        parking_movements,
        "register_exit",
        lambda user_id, parking_lot_id: {
            "parking_lot_id": parking_lot_id,
            "event_type": "exit",
            "occupied": 9,
            "capacity": 280,
        },
    )

    result = parking_movements.exit_parking_lot(
        "rodriguez-pena",
        TEST_USER,
    )

    assert result["message"] == "Egreso registrado correctamente"
    assert result["event_type"] == "exit"
    assert result["occupied"] == 9

def test_entry_translates_unique_user_constraint_to_conflict(monkeypatch):
    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, query, params=None):
            if "FROM parking_lots" in query:
                return FakeResult((1, 280))

            if "COUNT(*)" in query:
                return FakeResult((10,))

            if "FROM parked_vehicles" in query:
                return FakeResult(None)

            if "INSERT INTO parked_vehicles" in query:
                class FakeDiagnostic:
                    constraint_name = "parked_vehicles_user_id_key"

                class FakeUniqueViolation(errors.UniqueViolation):
                    @property
                    def diag(self):
                        return FakeDiagnostic()

                raise FakeUniqueViolation("duplicate user")

            raise AssertionError(f"Consulta inesperada: {query}")

    class FakeResult:
        def __init__(self, row):
            self.row = row

        def fetchone(self):
            return self.row

    monkeypatch.setattr(
        "app.repositories.parking_movement_repository.get_database_connection",
        lambda: FakeConnection(),
    )

    from app.repositories.parking_movement_repository import register_entry

    with pytest.raises(ParkingMovementConflict) as error:
        register_entry(999999, "rodriguez-pena")

    assert str(error.value) == "El usuario ya tiene un vehículo estacionado"
