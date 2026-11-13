from datetime import datetime, timezone

import psycopg

from app.repositories.parking_movement_repository import (
    ParkingLotNotFound,
    ParkingMovementConflict,
    get_active_vehicle,
    register_exit,
)
from app.repositories.user_repository import get_user_profile_by_id
from app.security.qr_tokens import (
    EXIT_QR_EXPIRE_MINUTES,
    create_exit_qr_token,
    decode_exit_qr_token,
)


class ExitQrError(Exception):
    """Error relacionado con la solicitud o validación de un QR de salida."""


class ExitQrUserNotFound(ExitQrError):
    pass


class ExitQrUserInactive(ExitQrError):
    pass


class ExitQrProfileIncomplete(ExitQrError):
    pass


class ExitQrNoActiveVehicle(ExitQrError):
    pass


class ExitQrParkingLotNotFound(ExitQrError):
    pass


class ExitQrInvalidToken(ExitQrError):
    pass


class ExitQrMovementConflict(ExitQrError):
    pass


class ExitQrDatabaseUnavailable(ExitQrError):
    pass


def request_exit_qr(user_id: int) -> dict:
    """Genera un QR de salida para el vehículo actualmente estacionado."""

    try:
        profile = get_user_profile_by_id(user_id)

        if profile is None:
            raise ExitQrUserNotFound(
                "No se encontró el usuario"
            )

        if profile["account_status"] != "active":
            raise ExitQrUserInactive(
                "La cuenta no está activa"
            )

        plate = profile["plate"]

        if not plate or not plate.strip():
            raise ExitQrProfileIncomplete(
                "El usuario no tiene una patente registrada"
            )

        active_vehicle = get_active_vehicle(user_id)

        if active_vehicle is None:
            raise ExitQrNoActiveVehicle(
                "No registrás un ingreso activo en el campus"
            )

        parking_lot_id = active_vehicle["parking_lot_id"]

        qr_token, expires_at = create_exit_qr_token(
            user_id=user_id,
            plate=plate,
            parking_lot_id=parking_lot_id,
            parked_vehicle_id=active_vehicle["parked_vehicle_id"],
        )

        return {
            "message": "QR de salida generado correctamente",
            "qr_token": qr_token,
            "plate": plate,
            "parking_lot": active_vehicle["parking_lot"],
            "expires_at": expires_at.isoformat(),
            "expires_in_seconds": EXIT_QR_EXPIRE_MINUTES * 60,
        }

    except ParkingLotNotFound as error:
        raise ExitQrParkingLotNotFound(str(error)) from error

    except psycopg.Error as error:
        raise ExitQrDatabaseUnavailable(
            "No se pudo consultar el ingreso activo"
        ) from error


def scan_exit_qr(qr_token: str) -> dict:
    """Valida un QR de salida y registra el egreso del vehículo."""

    payload = decode_exit_qr_token(qr_token)

    if payload is None:
        raise ExitQrInvalidToken(
            "El QR de salida es inválido o está vencido"
        )

    try:
        user_id = int(payload["sub"])
        profile = get_user_profile_by_id(user_id)

        if profile is None:
            raise ExitQrUserNotFound(
                "No se encontró el usuario asociado al QR"
            )

        if profile["account_status"] != "active":
            raise ExitQrUserInactive(
                "La cuenta no está activa"
            )

        if not profile["plate"] or profile["plate"] != payload["plate"]:
            raise ExitQrInvalidToken(
                "La patente del QR no coincide con la registrada"
            )

        active_vehicle = get_active_vehicle(user_id)

        if active_vehicle is None:
            raise ExitQrNoActiveVehicle(
                "El usuario no tiene un ingreso activo en el campus"
            )

        if (
            active_vehicle["parking_lot_id"] != payload["parking_lot_id"]
            or active_vehicle["parked_vehicle_id"]
            != payload["parked_vehicle_id"]
        ):
            raise ExitQrInvalidToken(
                "El QR no corresponde al ingreso activo actual"
            )

        try:
            movement = register_exit(
                user_id=user_id,
                parking_lot_id=payload["parking_lot_id"],
                expected_parked_vehicle_id=payload["parked_vehicle_id"],
            )
        except ParkingLotNotFound as error:
            raise ExitQrParkingLotNotFound(str(error)) from error
        except ParkingMovementConflict as error:
            raise ExitQrMovementConflict(str(error)) from error

        capacity = movement["capacity"]
        occupied = movement["occupied"]

        available = capacity - occupied

        occupancy_percentage = (
            round((occupied / capacity) * 100, 1)
            if capacity > 0
            else 0
        )

        return {
            "message": "Egreso registrado correctamente",
            "full_name": profile["full_name"],
            "plate": profile["plate"],
            "parking_lot": active_vehicle["parking_lot"],
            **movement,
            "available": available,
            "occupancy_percentage": occupancy_percentage,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

    except ParkingLotNotFound as error:
        raise ExitQrParkingLotNotFound(str(error)) from error

    except psycopg.Error as error:
        raise ExitQrDatabaseUnavailable(
            "No se pudo registrar el egreso"
        ) from error