import secrets

from argon2.exceptions import VerifyMismatchError

from app.security.passwords import password_hasher


def generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_verification_code(code: str) -> str:
    return password_hasher.hash(code)


def verify_verification_code(code_hash: str, code: str) -> bool:
    try:
        return password_hasher.verify(code_hash, code)
    except VerifyMismatchError:
        return False