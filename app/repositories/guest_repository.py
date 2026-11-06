from psycopg import errors

from app.database import get_database_connection
from app.repositories.parking_movement_repository import PARKING_LOT_IDS


class GuestVehicleError(Exception):
    """Error de negocio al administrar vehículos de invitados."""


class GuestParkingLotNotFound(GuestVehicleError):
    """El estacionamiento solicitado no existe."""


class GuestVehicleNotFound(GuestVehicleError):
    """El invitado no tiene un vehículo estacionado en ese lugar."""


class GuestVehicleConflict(GuestVehicleError):
    """El vehículo no puede registrarse en el estado actual."""


def _lock_parking_lot(connection, database_id: int) -> int:
    """Bloquea el estacionamiento para serializar los cambios de ocupación y devuelve su capacidad."""

    row = connection.execute(
        """
        SELECT total_slots
        FROM parking_lots
        WHERE id = %s
        FOR UPDATE
        """,
        (database_id,),
    ).fetchone()

    if row is None:
        raise GuestParkingLotNotFound(
            "El estacionamiento no existe en la base de datos"
        )

    return row[0]


def _count_occupied(connection, database_id: int) -> int:
    return connection.execute(
        """
        SELECT COUNT(*)
        FROM parked_vehicles
        WHERE parking_lot = %s
        """,
        (database_id,),
    ).fetchone()[0]


def insert_guest_vehicle(plate: str, created_by: int, parking_lot_id: str) -> dict:
    """Registra el vehículo de un invitado en el estacionamiento en una transacción."""

    database_id = PARKING_LOT_IDS.get(parking_lot_id)
    if database_id is None:
        raise GuestParkingLotNotFound("El estacionamiento solicitado no existe")

    with get_database_connection() as connection:
        capacity = _lock_parking_lot(connection, database_id)

        registered_user = connection.execute(
            'SELECT 1 FROM "user" WHERE plate = %s',
            (plate,),
        ).fetchone()

        if registered_user is not None:
            raise GuestVehicleConflict(
                "La patente pertenece a un usuario registrado"
            )

        # Si la patente ya existe, el UPDATE no cambia nada y devuelve su id.
        guest_id = connection.execute(
            """
            INSERT INTO guest (plate, created_by)
            VALUES (%s, %s)
            ON CONFLICT (plate) DO UPDATE SET plate = EXCLUDED.plate
            RETURNING id
            """,
            (plate, created_by),
        ).fetchone()[0]

        already_parked = connection.execute(
            """
            SELECT 1
            FROM parked_vehicles
            WHERE guest_id = %s
            """,
            (guest_id,),
        ).fetchone()

        if already_parked is not None:
            raise GuestVehicleConflict(
                "El vehículo del invitado ya se encuentra estacionado"
            )

        occupied = _count_occupied(connection, database_id)

        if occupied >= capacity:
            raise GuestVehicleConflict(
                "El estacionamiento no tiene lugares disponibles"
            )

        try:
            connection.execute(
                """
                INSERT INTO parked_vehicles (parking_lot, guest_id)
                VALUES (%s, %s)
                """,
                (database_id, guest_id),
            )
        except errors.UniqueViolation as exc:
            if exc.diag.constraint_name == "parked_vehicles_guest_id_key":
                raise GuestVehicleConflict(
                    "El vehículo del invitado ya se encuentra estacionado"
                ) from exc
            raise

    return {
        "parking_lot_id": parking_lot_id,
        "patente": plate,
        "occupied": occupied + 1,
        "capacity": capacity,
    }


def delete_guest_vehicle(plate: str, parking_lot_id: str) -> dict:
    """Quita el vehículo de un invitado del estacionamiento. El registro del invitado se conserva."""

    database_id = PARKING_LOT_IDS.get(parking_lot_id)
    if database_id is None:
        raise GuestParkingLotNotFound("El estacionamiento solicitado no existe")

    with get_database_connection() as connection:
        capacity = _lock_parking_lot(connection, database_id)

        vehicle = connection.execute(
            """
            DELETE FROM parked_vehicles AS pv
            USING guest AS g
            WHERE pv.guest_id = g.id
              AND g.plate = %s
              AND pv.parking_lot = %s
            RETURNING pv.id
            """,
            (plate, database_id),
        ).fetchone()

        if vehicle is None:
            raise GuestVehicleNotFound(
                "El invitado no tiene un vehículo estacionado en ese lugar"
            )

        occupied = _count_occupied(connection, database_id)

    return {
        "parking_lot_id": parking_lot_id,
        "patente": plate,
        "occupied": occupied,
        "capacity": capacity,
    }


def select_guest_vehicles(parking_lot_id: str) -> list[dict]:
    """Lista los vehículos de invitados estacionados, en orden de ingreso."""

    database_id = PARKING_LOT_IDS.get(parking_lot_id)
    if database_id is None:
        raise GuestParkingLotNotFound("El estacionamiento solicitado no existe")

    with get_database_connection() as connection:
        rows = connection.execute(
            """
            SELECT g.plate, pv.created_at
            FROM parked_vehicles AS pv
            JOIN guest AS g
                ON g.id = pv.guest_id
            WHERE pv.parking_lot = %s
            ORDER BY pv.created_at
            """,
            (database_id,),
        ).fetchall()

    return [
        {"patente": plate, "entered_at": entered_at}
        for plate, entered_at in rows
    ]
