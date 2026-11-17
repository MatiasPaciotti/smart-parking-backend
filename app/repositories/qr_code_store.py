import threading
from datetime import datetime, timedelta, timezone

from app.security.qr_codes import generate_qr_code


class QrCodeStore:
    """Guarda códigos temporales en memoria del proceso, sin base de datos."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._codes: dict[str, dict] = {}

    def create(self, record: dict, expires_minutes: int) -> tuple[str, datetime]:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)

        with self._lock:
            self._purge_expired()

            code = generate_qr_code()

            while code in self._codes:
                code = generate_qr_code()

            self._codes[code] = {
                **record,
                "expires_at": expires_at,
                "used": False,
            }

        return code, expires_at

    def get_active(self, code: str) -> dict | None:
        with self._lock:
            self._purge_expired()

            entry = self._codes.get(code)

            if entry is None or entry["used"]:
                return None

            return {
                key: value
                for key, value in entry.items()
                if key not in ("expires_at", "used")
            }

    def mark_used(self, code: str) -> None:
        with self._lock:
            if code in self._codes:
                self._codes[code]["used"] = True

    def _purge_expired(self) -> None:
        now = datetime.now(timezone.utc)

        expired_codes = [
            code
            for code, entry in self._codes.items()
            if entry["expires_at"] <= now
        ]

        for code in expired_codes:
            del self._codes[code]
