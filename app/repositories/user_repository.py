from app.database import get_database_connection
from app.schemas.user import UserRegistration, UserResponse
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
