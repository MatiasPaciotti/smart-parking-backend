from app.database import get_database_connection
from app.schemas.user import UserRegistration, UserResponse


def create_user(registration: UserRegistration, password_hash: str) -> UserResponse:
    with get_database_connection() as connection:
        row = connection.execute(
            """
            INSERT INTO "user" (
                full_name, email, role, account_status,
                is_on_campus, plate, dni, password_hash
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, full_name, email, role, account_status,
                      is_on_campus, plate, dni
            """,
            (
                f"{registration.nombre} {registration.apellido}",
                registration.email,
                "user",
                "active",
                False,
                registration.patente,
                registration.dni,
                password_hash,
            ),
        ).fetchone()

    return UserResponse(
        id=row[0],
        full_name=row[1],
        email=row[2],
        role=row[3],
        account_status=row[4],
        is_on_campus=row[5],
        plate=row[6],
        dni=row[7],
    )
