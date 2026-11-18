import secrets

ENTRY_QR_EXPIRE_MINUTES = 5
EXIT_QR_EXPIRE_MINUTES = 5

QR_CODE_LENGTH = 8
QR_CODE_PREFIX = "UNSAM-"

# Sin 0, O, 1, I ni L para que el código sea fácil de leer y tipear.
QR_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def generate_qr_code() -> str:
    """Genera un código corto y difícil de adivinar para un QR temporal."""

    return "".join(
        secrets.choice(QR_CODE_ALPHABET)
        for _ in range(QR_CODE_LENGTH)
    )


def normalize_qr_code(code: str) -> str:
    """Quita espacios, guiones y el prefijo UNSAM, y pasa el código a mayúsculas."""

    normalized = "".join(code.split()).upper()

    return normalized.removeprefix(QR_CODE_PREFIX).replace("-", "")
