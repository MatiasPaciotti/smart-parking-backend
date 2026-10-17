from app.database import get_database_connection
from app.schemas.user import UserRegistration, UserResponse
from datetime import datetime

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


def get_user_by_email(email: str) -> dict | None:
    """Busca un usuario por correo y devuelve los datos necesarios para autenticarlo."""
    with get_database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                full_name,
                email,
                role,
                password_hash,
                email_verified
            FROM "user"
            WHERE email = %s
            """,
            (email,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "full_name": row[1],
        "email": row[2],
        "role": row[3],
        "password_hash": row[4],
        "email_verified": row[5],
    }

def get_user_profile_by_id(user_id: int) -> dict | None:
    """Busca el perfil de un usuario por su identificador."""
    with get_database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                full_name,
                email,
                role,
                account_status,
                plate,
                dni,
                email_verified
            FROM "user"
            WHERE id = %s
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return None

    full_name = row[1]
    plate = row[5]
    dni = row[6]

    profile_complete = (
        bool(full_name and full_name.strip())
        and bool(plate and plate.strip())
        and dni is not None
    )

    return {
        "id": row[0],
        "full_name": full_name,
        "email": row[2],
        "role": row[3],
        "account_status": row[4],
        "plate": plate,
        "dni": dni,
        "email_verified": row[7],
        "profile_complete": profile_complete,
    }
