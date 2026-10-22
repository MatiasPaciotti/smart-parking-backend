
import os
from datetime import datetime, timedelta, timezone

import jwt

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(
    user_id: int,
    email: str,
    role: str,
    parking_lot_id: str | None = None,
) -> str:
    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("Falta configurar JWT_SECRET_KEY")

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }

    if parking_lot_id is not None:
        payload["parking_lot_id"] = parking_lot_id

    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Valida el JWT y devuelve sus datos, o None si no es válido."""
    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("Falta configurar JWT_SECRET_KEY")

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "email", "role", "iat", "exp"]},
        )

        # Verificar que el identificador tenga el formato esperado.
        int(payload["sub"])

        return payload

    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None
