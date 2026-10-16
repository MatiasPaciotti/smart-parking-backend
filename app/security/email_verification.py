
import hashlib
import hmac
import os
import secrets


def generate_verification_code() -> str:
    """Genera un código numérico de seis dígitos."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_verification_code(user_id: int, code: str) -> str:
    """Genera un hash del código asociado al usuario."""
    secret = os.getenv("EMAIL_VERIFICATION_SECRET")

    if not secret:
        raise RuntimeError(
            "Falta configurar EMAIL_VERIFICATION_SECRET"
        )

    message = f"{user_id}:{code}".encode("utf-8")

    return hmac.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


def verify_verification_code(
    user_id: int,
    code: str,
    stored_hash: str,
) -> bool:
    """Comprueba si el código coincide con el hash guardado."""
    calculated_hash = hash_verification_code(user_id, code)

    return hmac.compare_digest(calculated_hash, stored_hash)
