from datetime import datetime

from app.repositories.qr_code_store import QrCodeStore
from app.security.qr_codes import EXIT_QR_EXPIRE_MINUTES

_exit_qr_codes = QrCodeStore()


def create_exit_qr_code(
    user_id: int,
    plate: str,
    parking_lot_id: str,
    parked_vehicle_id: int,
) -> tuple[str, datetime]:
    """Guarda un código de salida vigente y devuelve el código y su vencimiento."""

    return _exit_qr_codes.create(
        {
            "user_id": user_id,
            "plate": plate,
            "parking_lot_id": parking_lot_id,
            "parked_vehicle_id": parked_vehicle_id,
        },
        EXIT_QR_EXPIRE_MINUTES,
    )


def get_active_exit_qr_code(code: str) -> dict | None:
    """Devuelve los datos de un código de salida que todavía no venció ni fue usado."""

    return _exit_qr_codes.get_active(code)


def mark_exit_qr_code_used(code: str) -> None:
    """Marca el código como usado para que no pueda registrar otro egreso."""

    _exit_qr_codes.mark_used(code)
