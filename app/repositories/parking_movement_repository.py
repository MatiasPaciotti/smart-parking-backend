
from psycopg import errors

from app.database import get_database_connection

PARKING_LOT_IDS = {
    "rodriguez-pena": 1,
    "tornavias": 2,
}

PARKING_LOT_IDS_BY_DATABASE_ID = {
    database_id: parking_lot_id
    for parking_lot_id, database_id in PARKING_LOT_IDS.items()
}


class ParkingMovementError(Exception):
    """Error de negocio al registrar un movimiento de estacionamiento."""


class ParkingLotNotFound(ParkingMovementError):
    """El estacionamiento solicitado no existe."""


class ParkingMovementConflict(ParkingMovementError):
    """El movimiento no puede realizarse en el estado actual."""


def register_entry(user_id: int, parking_lot_id: str) -> dict:
    """Registra el ingreso del usuario y su vehículo en una transacción."""

    database_id = PARKING_LOT_IDS.get(parking_lot_id)
    if database_id is None:
        raise ParkingLotNotFound("El estacionamiento solicitado no existe")

    with get_database_connection() as connection:
        parking_lot = connection.execute(
            """
            SELECT id, total_slots
            FROM parking_lots
            WHERE id = %s
            FOR UPDATE
            """,
            (database_id,),
        ).fetchone()

        if parking_lot is None:
            raise ParkingLotNotFound(
                "El estacionamiento no existe en la base de datos"
            )

        existing_vehicle = connection.execute(
            """
            SELECT parking_lot
            FROM parked_vehicles
            WHERE user_id = %s
            """,
            (user_id,),
        ).fetchone()

        if existing_vehicle is not None:
            raise ParkingMovementConflict(
                "El usuario ya tiene un vehículo estacionado"
            )

        occupied = connection.execute(
            """
            SELECT COUNT(*)
            FROM parked_vehicles
            WHERE parking_lot = %s
            """,
            (database_id,),
        ).fetchone()[0]

        if occupied >= parking_lot[1]:
            raise ParkingMovementConflict(
                "El estacionamiento no tiene lugares disponibles"
            )

        try:
            connection.execute(
                """
                INSERT INTO parked_vehicles (parking_lot, user_id)
                VALUES (%s, %s)
                """,
                (database_id, user_id),
            )
        except errors.UniqueViolation as exc:
            if exc.diag.constraint_name == "parked_vehicles_user_id_key":
                raise ParkingMovementConflict(
                    "El usuario ya tiene un vehículo estacionado"
                ) from exc
            raise

    return {
        "parking_lot_id": parking_lot_id,
        "event_type": "entry",
        "occupied": occupied + 1,
        "capacity": parking_lot[1],
    }


def register_exit(
    user_id: int,
    parking_lot_id: str,
    expected_parked_vehicle_id: int | None = None,
) -> dict:
    """Registra la salida del vehículo en una transacción."""

    database_id = PARKING_LOT_IDS.get(parking_lot_id)

    if database_id is None:
        raise ParkingLotNotFound(
            "El estacionamiento solicitado no existe"
        )

    with get_database_connection() as connection:
        parking_lot = connection.execute(
            """
            SELECT id, total_slots
            FROM parking_lots
            WHERE id = %s
            FOR UPDATE
            """,
            (database_id,),
        ).fetchone()

        if parking_lot is None:
            raise ParkingLotNotFound(
                "El estacionamiento no existe en la base de datos"
            )

        if expected_parked_vehicle_id is not None:
            vehicle = connection.execute(
                """
                DELETE FROM parked_vehicles
                WHERE user_id = %s
                  AND parking_lot = %s
                  AND id = %s
                RETURNING id
                """,
                (
                    user_id,
                    database_id,
                    expected_parked_vehicle_id,
                ),
            ).fetchone()
        else:
            vehicle = connection.execute(
                """
                DELETE FROM parked_vehicles
                WHERE user_id = %s
                  AND parking_lot = %s
                RETURNING id
                """,
                (user_id, database_id),
            ).fetchone()

        if vehicle is None:
            raise ParkingMovementConflict(
                "El usuario no tiene un vehículo estacionado en ese lugar"
            )

        occupied = connection.execute(
            """
            SELECT COUNT(*)
            FROM parked_vehicles
            WHERE parking_lot = %s
            """,
            (database_id,),
        ).fetchone()[0]

    return {
        "parking_lot_id": parking_lot_id,
        "event_type": "exit",
        "occupied": occupied,
        "capacity": parking_lot[1],
    }

def has_active_vehicle(user_id: int) -> bool:
    """Indica si el usuario tiene un vehículo actualmente estacionado."""

    with get_database_connection() as connection:
        row = connection.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM parked_vehicles
                WHERE user_id = %s
            )
            """,
            (user_id,),
        ).fetchone()

    return bool(row[0])

def get_active_vehicle(user_id: int) -> dict | None:
    """Obtiene el estacionamiento donde está actualmente el usuario."""

    with get_database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                pv.id,
		pv.parking_lot,
                pl.name
            FROM parked_vehicles AS pv
            JOIN parking_lots AS pl
                ON pl.id = pv.parking_lot
            WHERE pv.user_id = %s
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return None

    parking_lot_id = PARKING_LOT_IDS_BY_DATABASE_ID.get(row[1])

    if parking_lot_id is None:
        raise ParkingLotNotFound(
            "El estacionamiento asociado al vehículo no existe"
        )

    return {
        "parked_vehicle_id": row[0],
        "parking_lot_id": parking_lot_id,
        "parking_lot": {
            "id": parking_lot_id,
            "name": row[2],
        },
    }