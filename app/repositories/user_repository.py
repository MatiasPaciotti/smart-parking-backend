from app.database import get_database_connection
from app.schemas.user import UserRegistration, UserResponse
from datetime import datetime
from app.security.verification_codes import verify_verification_code


def create_user(
    registration: UserRegistration,
    password_hash: str,
    verification_code_hash: str,
) -> UserResponse:
    with get_database_connection() as connection:
        row = connection.execute(
            """
            INSERT INTO "user" (
                full_name, email, role, account_status,
                                is_on_campus, plate, dni, password_hash,
                                email_verified, verification_code_hash,
                                verification_code_expires_at, verification_attempts,
                                verification_resend_count, verification_resend_window_started_at
            )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s,
                                        NOW() + INTERVAL '10 minutes', 0, 0, NOW())
            RETURNING id, full_name, email, role, account_status,
                                            is_on_campus, plate, dni, email_verified
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
                verification_code_hash,
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
        email_verified=row[8],
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
def verify_user_email(email: str, code: str) -> bool:
    with get_database_connection() as connection:
        row = connection.execute(
            """
            SELECT id, email_verified, verification_code_hash,
                   verification_attempts,
                   verification_code_expires_at > NOW()
            FROM "user"
            WHERE email = %s
            FOR UPDATE
            """,
            (email,),
        ).fetchone()
        if (
            row is None
            or row[1]
            or row[2] is None
            or not row[4]
            or row[3] >= 5
        ):
            return False

        if not verify_verification_code(row[2], code):
            connection.execute(
                'UPDATE "user" SET verification_attempts = verification_attempts + 1 WHERE id = %s',
                (row[0],),
            )
            return False

        connection.execute(
            """
            UPDATE "user"
            SET email_verified = TRUE,
                verification_code_hash = NULL,
                verification_code_expires_at = NULL,
                verification_attempts = 0
            WHERE id = %s
            """,
            (row[0],),
        )
    return True


def replace_verification_code(email: str, code_hash: str) -> bool:
    with get_database_connection() as connection:
        row = connection.execute(
            """
            UPDATE "user"
            SET verification_code_hash = %s,
                verification_code_expires_at = NOW() + INTERVAL '10 minutes',
                verification_attempts = 0,
                verification_resend_count = CASE
                    WHEN verification_resend_window_started_at IS NULL
                         OR verification_resend_window_started_at <= NOW() - INTERVAL '1 hour'
                    THEN 1
                    ELSE verification_resend_count + 1
                END,
                verification_resend_window_started_at = CASE
                    WHEN verification_resend_window_started_at IS NULL
                         OR verification_resend_window_started_at <= NOW() - INTERVAL '1 hour'
                    THEN NOW()
                    ELSE verification_resend_window_started_at
                END
            WHERE email = %s
              AND email_verified = FALSE
              AND (
                  verification_resend_window_started_at IS NULL
                  OR verification_resend_window_started_at <= NOW() - INTERVAL '1 hour'
                  OR verification_resend_count < 3
              )
            RETURNING id
            """,
            (code_hash, email),
        ).fetchone()
    return row is not None
