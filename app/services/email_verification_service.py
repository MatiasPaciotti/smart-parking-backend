from app.services.email_sender import (
    send_verification_email,
    EmailSendingError,
)

from datetime import datetime, timedelta, timezone

from app.repositories.user_repository import (
    get_user_by_email,
    save_email_verification_code,
)
from app.security.email_verification import (
    generate_verification_code,
    hash_verification_code,
)


CODE_EXPIRATION_MINUTES = 10


class UserNotFoundError(Exception):
    pass


class EmailAlreadyVerifiedError(Exception):
    pass


class VerificationCodeSaveError(Exception):
    pass



def create_email_verification(email: str) -> dict:
    """Genera, guarda y envía un código de verificación."""
    user = get_user_by_email(email)

    if user is None:
        raise UserNotFoundError

    if user["email_verified"]:
        raise EmailAlreadyVerifiedError

    code = generate_verification_code()
    code_hash = hash_verification_code(user["id"], code)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=CODE_EXPIRATION_MINUTES
    )

    saved = save_email_verification_code(
        user_id=user["id"],
        code_hash=code_hash,
        expires_at=expires_at,
    )

    if not saved:
        raise VerificationCodeSaveError

    try:
        send_verification_email(
            email=user["email"],
            code=code,
        )
    except EmailSendingError as error:
        raise VerificationEmailSendingError from error

    return {
        "email": user["email"],
        "expires_at": expires_at,
    }

class VerificationEmailSendingError(Exception):
    pass

from app.repositories.user_repository import (
    get_email_verification_data,
    increment_verification_attempts,
    mark_email_verified,
)
from app.security.email_verification import verify_verification_code


class InvalidVerificationCodeError(Exception):
    pass


class ExpiredVerificationCodeError(Exception):
    pass


class TooManyVerificationAttemptsError(Exception):
    pass


def confirm_email_verification(email: str, code: str) -> dict:
    """Comprueba el código y marca el correo como verificado."""
    verification = get_email_verification_data(email)

    if verification is None:
        raise UserNotFoundError

    if verification["email_verified"]:
        raise EmailAlreadyVerifiedError

    if verification["attempts"] >= 5:
        raise TooManyVerificationAttemptsError

    stored_hash = verification["code_hash"]
    expires_at = verification["expires_at"]

    if not stored_hash or not expires_at:
        raise InvalidVerificationCodeError

    now = datetime.now(timezone.utc)

    if expires_at <= now:
        raise ExpiredVerificationCodeError

    if not verify_verification_code(
        verification["id"],
        code,
        stored_hash,
    ):
        attempts = increment_verification_attempts(verification["id"])

        if attempts is None or attempts >= 5:
            raise TooManyVerificationAttemptsError

        raise InvalidVerificationCodeError

    verified = mark_email_verified(
        user_id=verification["id"],
        code_hash=stored_hash,
        now=now,
    )

    if not verified:
        raise InvalidVerificationCodeError

    return {
        "email": email,
        "email_verified": True,
    }
