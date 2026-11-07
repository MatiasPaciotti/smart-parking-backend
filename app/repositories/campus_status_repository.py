from app.database import get_database_connection


def get_campus_status_by_user_id(user_id: int) -> dict | None:
    """Obtiene el estado de presencia de un usuario en el campus."""

    with get_database_connection() as connection:
        row = connection.execute(
            """
            SELECT account_status, is_on_campus
            FROM "user"
            WHERE id = %s
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "account_status": row[0],
        "is_on_campus": bool(row[1]),
    }