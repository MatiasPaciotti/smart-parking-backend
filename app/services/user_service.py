import psycopg

from app.repositories.user_repository import (
    create_user,
    replace_verification_code,
    verify_user_email,
)
from app.schemas.user import UserRegistration, UserResponse
from app.security.passwords import hash_password
from app.security.verification_codes import (
    generate_verification_code,
    hash_verification_code,
)


class DuplicatePlateError(Exception):
    pass


class DuplicateEmailError(Exception):
    pass


class DuplicateDataError(Exception):
    pass


class DatabaseUnavailableError(Exception):
    pass


def register_user(registration: UserRegistration) -> tuple[UserResponse, str]:
    password_hash = hash_password(registration.password.get_secret_value())
    code = generate_verification_code()
    code_hash = hash_verification_code(code)
    try:
        user = create_user(registration, password_hash, code_hash)
        return user, code
    except psycopg.errors.UniqueViolation as error:
        constraint_name = error.diag.constraint_name
        if constraint_name == "user_plate_key":
            raise DuplicatePlateError from error
        if constraint_name == "user_email_key":
            raise DuplicateEmailError from error
        raise DuplicateDataError from error
    except (psycopg.Error, ValueError) as error:
        raise DatabaseUnavailableError from error


def verify_email_code(email: str, code: str) -> bool:
    try:
        return verify_user_email(email, code)
    except psycopg.Error as error:
        raise DatabaseUnavailableError from error


def resend_email_code(email: str) -> tuple[bool, str]:
    code = generate_verification_code()
    code_hash = hash_verification_code(code)
    try:
        return replace_verification_code(email, code_hash), code
    except psycopg.Error as error:
        raise DatabaseUnavailableError from error
