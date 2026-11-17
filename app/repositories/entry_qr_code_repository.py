from datetime import datetime

from app.repositories.qr_code_store import QrCodeStore
from app.security.qr_codes import ENTRY_QR_EXPIRE_MINUTES

_entry_qr_codes = QrCodeStore()


def create_entry_qr_code(
    user_id: int,
    plate: str,
    parking_lot_id: str,
) -> tuple[str, datetime]:
    """Guarda un código de entrada vigente y devuelve el código y su vencimiento."""

    return _entry_qr_codes.create(
        {
            "user_id": user_id,
            "plate": plate,
            "parking_lot_id": parking_lot_id,
        },
        ENTRY_QR_EXPIRE_MINUTES,
    )


def get_active_entry_qr_code(code: str) -> dict | None:
    """Devuelve los datos de un código de entrada que todavía no venció ni fue usado."""

    return _entry_qr_codes.get_active(code)


def mark_entry_qr_code_used(code: str) -> None:
    """Marca el código como usado para que no pueda registrar otro ingreso."""

    _entry_qr_codes.mark_used(code)
