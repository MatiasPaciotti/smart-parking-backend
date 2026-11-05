import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from app.security.tokens import ALGORITHM

ENTRY_QR_EXPIRE_MINUTES = 5
EXIT_QR_EXPIRE_MINUTES = 5

ENTRY_QR_PURPOSE = "parking_entry"
EXIT_QR_PURPOSE = "parking_exit"


def _create_qr_token(
    user_id: int,
    plate: str,
    parking_lot_id: str,
    purpose: str,
    expires_minutes: int,
    parked_vehicle_id: int | None = None,
) -> tuple[str, datetime]:
    """Genera un JWT temporal para una operación de estacionamiento."""

    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("Falta configurar JWT_SECRET_KEY")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=expires_minutes)

    payload = {
        "sub": str(user_id),
        "plate": plate,
        "parking_lot_id": parking_lot_id,
        "purpose": purpose,
        "jti": str(uuid4()),
        "iat": now,
        "exp": expires_at,
    }

    if parked_vehicle_id is not None:
        payload["parked_vehicle_id"] = parked_vehicle_id

    token = jwt.encode(
        payload,
        secret_key,
        algorithm=ALGORITHM,
    )

    return token, expires_at


def _decode_qr_token(
    token: str,
    expected_purpose: str,
) -> dict | None:
    """Valida la firma, vigencia y propósito de un QR."""

    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("Falta configurar JWT_SECRET_KEY")

    required_claims = [
        "sub",
        "plate",
        "parking_lot_id",
        "purpose",
        "jti",
        "iat",
        "exp",
    ]

    if expected_purpose == EXIT_QR_PURPOSE:
        required_claims.append("parked_vehicle_id")

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[ALGORITHM],
            options={"require": required_claims},
        )

        if payload["purpose"] != expected_purpose:
            return None

        if int(payload["sub"]) <= 0:
            return None

        for field in ("plate", "parking_lot_id", "jti"):
            if not isinstance(payload[field], str) or not payload[field].strip():
                return None

        if expected_purpose == EXIT_QR_PURPOSE:
            vehicle_id = payload["parked_vehicle_id"]

            if type(vehicle_id) is not int or vehicle_id <= 0:
                return None

        return payload

    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None


def create_entry_qr_token(
    user_id: int,
    plate: str,
    parking_lot_id: str,
) -> tuple[str, datetime]:
    """Genera un QR temporal de entrada."""

    return _create_qr_token(
        user_id=user_id,
        plate=plate,
        parking_lot_id=parking_lot_id,
        purpose=ENTRY_QR_PURPOSE,
        expires_minutes=ENTRY_QR_EXPIRE_MINUTES,
    )


def decode_entry_qr_token(token: str) -> dict | None:
    """Valida un QR de entrada."""

    return _decode_qr_token(token, ENTRY_QR_PURPOSE)


def create_exit_qr_token(
    user_id: int,
    plate: str,
    parking_lot_id: str,
    parked_vehicle_id: int,
) -> tuple[str, datetime]:
    """Genera un QR temporal de salida vinculado al ingreso actual."""

    return _create_qr_token(
        user_id=user_id,
        plate=plate,
        parking_lot_id=parking_lot_id,
        purpose=EXIT_QR_PURPOSE,
        expires_minutes=EXIT_QR_EXPIRE_MINUTES,
        parked_vehicle_id=parked_vehicle_id,
    )


def decode_exit_qr_token(token: str) -> dict | None:
    """Valida un QR de salida."""

    return _decode_qr_token(token, EXIT_QR_PURPOSE)