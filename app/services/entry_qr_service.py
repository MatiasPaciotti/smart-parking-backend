import psycopg

from app.repositories.entry_qr_code_repository import (
    create_entry_qr_code,
    get_active_entry_qr_code,
    mark_entry_qr_code_used,
)
from app.repositories.occupancy_repository import get_parking_occupancy
from app.repositories.parking_movement_repository import (
    ParkingLotNotFound,
    ParkingMovementConflict,
    has_active_vehicle,
    register_entry,
)
from app.repositories.user_repository import get_user_profile_by_id
from app.schemas.user import EMAIL_PATTERN
from app.security.qr_codes import (
    ENTRY_QR_EXPIRE_MINUTES,
    normalize_qr_code,
)


class EntryQrError(Exception):
    """Error relacionado con la solicitud de un QR de entrada."""


class EntryQrUserNotFound(EntryQrError):
    pass


class EntryQrProfileIncomplete(EntryQrError):
    pass


class EntryQrUserInactive(EntryQrError):
    pass


class EntryQrUserAlreadyInside(EntryQrError):
    pass


class EntryQrParkingLotNotFound(EntryQrError):
    pass


class EntryQrParkingLotFull(EntryQrError):
    pass


class EntryQrDatabaseUnavailable(EntryQrError):
    pass


class EntryQrInvalidToken(EntryQrError):
    pass


class EntryQrMovementConflict(EntryQrError):
    pass


class EntryQrUserNotEligible(EntryQrError):
    pass


def _validate_entry_profile(profile: dict) -> str:
    """Comprueba que el usuario esté autorizado para ingresar."""

    if profile["account_status"] != "active":
        raise EntryQrUserInactive(
            "La cuenta no está activa"
        )

    if profile.get("role") != "user":
        raise EntryQrUserNotEligible(
            "Solo los usuarios de la comunidad UNSAM pueden ingresar"
        )

    if profile.get("email_verified") is not True:
        raise EntryQrUserNotEligible(
            "Debés verificar tu correo institucional antes de ingresar"
        )

    email = profile.get("email")

    if (
        not isinstance(email, str)
        or EMAIL_PATTERN.fullmatch(email.strip()) is None
    ):
        raise EntryQrUserNotEligible(
            "El acceso requiere un correo institucional de UNSAM"
        )

    plate = profile.get("plate")

    if not isinstance(plate, str) or not plate.strip():
        raise EntryQrProfileIncomplete(
            "Primero tenés que registrar la patente de tu vehículo"
        )

    return plate


def request_entry_qr(user_id: int, parking_lot_id: str) -> dict:
    """Valida las condiciones de ingreso y genera un QR temporal."""

    try:
        profile = get_user_profile_by_id(user_id)

        if profile is None:
            raise EntryQrUserNotFound(
                "No se encontró el usuario"
            )

        plate = _validate_entry_profile(profile)

        if has_active_vehicle(user_id):
            raise EntryQrUserAlreadyInside(
                "Ya tenés un ingreso activo en el campus"
            )

        occupancy = get_parking_occupancy(parking_lot_id)

        if occupancy is None:
            raise EntryQrParkingLotNotFound(
                "El estacionamiento solicitado no existe"
            )

        if occupancy["available"] <= 0:
            raise EntryQrParkingLotFull(
                "Estacionamiento Completo"
            )

        qr_code, expires_at = create_entry_qr_code(
            user_id=user_id,
            plate=plate,
            parking_lot_id=parking_lot_id,
        )

        return {
            "message": "QR de entrada generado correctamente",
            "qr_token": qr_code,
            "code": qr_code,
            "plate": plate,
            "parking_lot": occupancy["parking_lot"],
            "expires_at": expires_at.isoformat(),
            "expires_in_seconds": ENTRY_QR_EXPIRE_MINUTES * 60,
        }

    except psycopg.Error as error:
        raise EntryQrDatabaseUnavailable(
            "No se pudo consultar la información del estacionamiento"
        ) from error


def scan_entry_qr(qr_code: str) -> dict:
    """Valida un código de entrada y registra el ingreso del vehículo."""

    normalized_code = normalize_qr_code(qr_code)

    try:
        entry_qr = get_active_entry_qr_code(normalized_code)

        if entry_qr is None:
            raise EntryQrInvalidToken(
                "El QR es inválido o está vencido"
            )

        user_id = entry_qr["user_id"]
        profile = get_user_profile_by_id(user_id)

        if profile is None:
            raise EntryQrUserNotFound(
                "No se encontró el usuario asociado al QR"
            )

        plate = _validate_entry_profile(profile)

        if plate != entry_qr["plate"]:
            raise EntryQrInvalidToken(
                "La patente del QR no coincide con la registrada"
            )

        try:
            movement = register_entry(
                user_id=user_id,
                parking_lot_id=entry_qr["parking_lot_id"],
            )
        except ParkingLotNotFound as exc:
            raise EntryQrParkingLotNotFound(str(exc)) from exc
        except ParkingMovementConflict as exc:
            raise EntryQrMovementConflict(str(exc)) from exc

        mark_entry_qr_code_used(normalized_code)

        return {
            "message": "Ingreso registrado correctamente",
            "full_name": profile["full_name"],
            "plate": profile["plate"],
            **movement,
        }

    except psycopg.Error as exc:
        raise EntryQrDatabaseUnavailable(
            "No se pudo registrar el ingreso"
        ) from exc