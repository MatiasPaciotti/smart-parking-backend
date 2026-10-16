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

def save_email_verification_code(
    user_id: int,
    code_hash: str,
    expires_at: datetime,
) -> bool:
    """Guarda el hash y el vencimiento del código de verificación."""
    with get_database_connection() as connection:
        row = connection.execute(
            """
            UPDATE "user"
            SET
                verification_code_hash = %s,
                verification_code_expires_at = %s,
                verification_attempts = 0
            WHERE id = %s
              AND email_verified = FALSE
            RETURNING id
            """,
            (code_hash, expires_at, user_id),
        ).fetchone()

    return row is not None

def get_email_verification_data(email: str) -> dict | None:
    """Obtiene los datos necesarios para verificar el correo."""
    with get_database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                email_verified,
                verification_code_hash,
                verification_code_expires_at,
                verification_attempts
            FROM "user"
            WHERE email = %s
            """,
            (email,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "email_verified": row[1],
        "code_hash": row[2],
        "expires_at": row[3],
        "attempts": row[4],
    }


def increment_verification_attempts(user_id: int) -> int | None:
    """Incrementa los intentos si todavía no se alcanzó el límite."""
    with get_database_connection() as connection:
        row = connection.execute(
            """
            UPDATE "user"
            SET verification_attempts = verification_attempts + 1
            WHERE id = %s
              AND email_verified = FALSE
              AND verification_attempts < 5
            RETURNING verification_attempts
            """,
            (user_id,),
        ).fetchone()

    return row[0] if row else None


def mark_email_verified(
    user_id: int,
    code_hash: str,
    now: datetime,
) -> bool:
    """Marca el correo como verificado si el código sigue vigente."""
    with get_database_connection() as connection:
        row = connection.execute(
            """
            UPDATE "user"
            SET
                email_verified = TRUE,
                verification_code_hash = NULL,
                verification_code_expires_at = NULL,
                verification_attempts = 0
            WHERE id = %s
              AND email_verified = FALSE
              AND verification_attempts < 5
              AND verification_code_hash = %s
              AND verification_code_expires_at > %s
            RETURNING id
            """,
            (user_id, code_hash, now),
        ).fetchone()

    return row is not None


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
