import psycopg

from app.repositories.user_repository import create_user
from app.schemas.user import UserRegistration, UserResponse
from app.security.passwords import hash_password


class DuplicatePlateError(Exception):
    pass


class DuplicateEmailError(Exception):
    pass


class DuplicateDataError(Exception):
    pass


class DatabaseUnavailableError(Exception):
    pass


def register_user(registration: UserRegistration) -> UserResponse:
    password_hash = hash_password(registration.password.get_secret_value())
    try:
        return create_user(registration, password_hash)
    except psycopg.errors.UniqueViolation as error:
        constraint_name = error.diag.constraint_name
        if constraint_name == "user_plate_key":
            raise DuplicatePlateError from error
        if constraint_name == "user_email_key":
            raise DuplicateEmailError from error
        raise DuplicateDataError from error
    except (psycopg.Error, ValueError) as error:
        raise DatabaseUnavailableError from error
