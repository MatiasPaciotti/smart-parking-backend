import psycopg

from app.repositories.occupancy_repository import get_parking_occupancy
from app.repositories.parking_movement_repository import (
    ParkingLotNotFound,
    ParkingMovementConflict,
    has_active_vehicle,
    register_entry,
)
from app.repositories.user_repository import get_user_profile_by_id
from app.security.qr_tokens import (
    ENTRY_QR_EXPIRE_MINUTES,
    create_entry_qr_token,
    decode_entry_qr_token,
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


def request_entry_qr(user_id: int, parking_lot_id: str) -> dict:
    """Valida las condiciones de ingreso y genera un QR temporal."""

    try:
        profile = get_user_profile_by_id(user_id)

        if profile is None:
            raise EntryQrUserNotFound(
                "No se encontró el usuario"
            )

        if profile["account_status"] != "active":
            raise EntryQrUserInactive(
                "La cuenta no está activa"
            )

        plate = profile["plate"]

        if not plate or not plate.strip():
            raise EntryQrProfileIncomplete(
                "Primero tenés que registrar la patente de tu vehículo"
            )

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

        qr_token, expires_at = create_entry_qr_token(
            user_id=user_id,
            plate=plate,
            parking_lot_id=parking_lot_id,
        )

        return {
            "message": "QR de entrada generado correctamente",
            "qr_token": qr_token,
            "plate": plate,
            "parking_lot": occupancy["parking_lot"],
            "expires_at": expires_at.isoformat(),
            "expires_in_seconds": ENTRY_QR_EXPIRE_MINUTES * 60,
        }

    except psycopg.Error as error:
        raise EntryQrDatabaseUnavailable(
            "No se pudo consultar la información del estacionamiento"
        ) from error


def scan_entry_qr(qr_token: str) -> dict:
    """Valida un QR de entrada y registra el ingreso del vehículo."""

    payload = decode_entry_qr_token(qr_token)

    if payload is None:
        raise EntryQrInvalidToken(
            "El QR es inválido o está vencido"
        )

    try:
        user_id = int(payload["sub"])
        profile = get_user_profile_by_id(user_id)

        if profile is None:
            raise EntryQrUserNotFound(
                "No se encontró el usuario asociado al QR"
            )

        if profile["account_status"] != "active":
            raise EntryQrUserInactive(
                "La cuenta no está activa"
            )

        if not profile["plate"] or profile["plate"] != payload["plate"]:
            raise EntryQrInvalidToken(
                "La patente del QR no coincide con la registrada"
            )

        try:
            movement = register_entry(
                user_id=user_id,
                parking_lot_id=payload["parking_lot_id"],
            )
        except ParkingLotNotFound as exc:
            raise EntryQrParkingLotNotFound(str(exc)) from exc
        except ParkingMovementConflict as exc:
            raise EntryQrMovementConflict(str(exc)) from exc

        return {
            "message": "Ingreso registrado correctamente",
            "plate": profile["plate"],
            **movement,
        }

    except psycopg.Error as exc:
        raise EntryQrDatabaseUnavailable(
            "No se pudo registrar el ingreso"
        ) from exc