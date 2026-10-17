
from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Genera un hash seguro para almacenar la contraseña."""
    return password_hasher.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    """Comprueba una contraseña contra el hash almacenado."""
    try:
        return password_hasher.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
