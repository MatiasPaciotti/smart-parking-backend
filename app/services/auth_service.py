import psycopg

from app.repositories.user_repository import get_user_by_email
from app.security.passwords import verify_password
from app.services.user_service import DatabaseUnavailableError


class InvalidCredentialsError(Exception):
    pass


def authenticate_user(email: str, password: str) -> dict:
    try:
        user = get_user_by_email(email)
    except (psycopg.Error, ValueError) as error:
        raise DatabaseUnavailableError from error

    if user is None:
        raise InvalidCredentialsError

    if not verify_password(password, user["password_hash"]):
        raise InvalidCredentialsError

    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "role": user["role"],
    }