
from app.database import get_database_connection


def get_parking_occupancy(parking_lot_id: str) -> dict | None:
    """Consulta la capacidad y los vehículos registrados de un estacionamiento."""

    parking_lot_ids = {
        "rodriguez-pena": 1,
        "tornavias": 2,
    }

    database_id = parking_lot_ids.get(parking_lot_id)

    if database_id is None:
        return None

    with get_database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                pl.id,
                pl.name,
                pl.total_slots,
                COUNT(pv.id) AS occupied
            FROM parking_lots AS pl
            LEFT JOIN parked_vehicles AS pv
                ON pv.parking_lot = pl.id
            WHERE pl.id = %s
            GROUP BY pl.id, pl.name, pl.total_slots
            """,
            (database_id,),
        ).fetchone()

    if row is None:
        return None

    capacity = row[2]
    occupied = row[3]

    if capacity <= 0:
        raise ValueError("La capacidad del estacionamiento debe ser mayor que cero")

    if occupied > capacity:
        raise ValueError("Los vehículos registrados superan la capacidad del estacionamiento")

    available = capacity - occupied
    percentage = round((occupied / capacity) * 100, 1)

    if percentage < 70:
        traffic_light = "green"
    elif percentage <= 95:
        traffic_light = "yellow"
    else:
        traffic_light = "red"

    return {
        "parking_lot": {
            "id": row[0],
            "name": row[1],
        },
        "capacity": capacity,
        "occupied": occupied,
        "available": available,
        "occupancy_percentage": percentage,
        "traffic_light": traffic_light,
    }
