import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from app.security.tokens import ALGORITHM

ENTRY_QR_EXPIRE_MINUTES = 5
ENTRY_QR_PURPOSE = "parking_entry"


def create_entry_qr_token(
    user_id: int,
    plate: str,
    parking_lot_id: str,
) -> tuple[str, datetime]:
    """Genera un JWT temporal para autorizar un ingreso."""

    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("Falta configurar JWT_SECRET_KEY")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=ENTRY_QR_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "plate": plate,
        "parking_lot_id": parking_lot_id,
        "purpose": ENTRY_QR_PURPOSE,
        "jti": str(uuid4()),
        "iat": now,
        "exp": expires_at,
    }

    token = jwt.encode(
        payload,
        secret_key,
        algorithm=ALGORITHM,
    )

    return token, expires_at


def decode_entry_qr_token(token: str) -> dict | None:
    """Valida el JWT de entrada y devuelve sus datos."""

    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("Falta configurar JWT_SECRET_KEY")

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[ALGORITHM],
            options={
                "require": [
                    "sub",
                    "plate",
                    "parking_lot_id",
                    "purpose",
                    "jti",
                    "iat",
                    "exp",
                ],
            },
        )

        if payload["purpose"] != ENTRY_QR_PURPOSE:
            return None

        int(payload["sub"])

        for field in ("plate", "parking_lot_id", "jti"):
            if not isinstance(payload[field], str) or not payload[field].strip():
                return None

        return payload

    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None