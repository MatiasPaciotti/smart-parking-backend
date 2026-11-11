from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser
from app.schemas.qr import EntryQrScanRequest
from app.services.entry_qr_service import (
    EntryQrDatabaseUnavailable,
    EntryQrInvalidToken,
    EntryQrMovementConflict,
    EntryQrParkingLotFull,
    EntryQrParkingLotNotFound,
    EntryQrProfileIncomplete,
    EntryQrUserAlreadyInside,
    EntryQrUserInactive,
    EntryQrUserNotFound,
    request_entry_qr,
)
from app.services.entry_qr_service import (
    scan_entry_qr as process_entry_qr_scan,
)
from app.services.exit_qr_service import (
    ExitQrDatabaseUnavailable,
    ExitQrInvalidToken,
    ExitQrMovementConflict,
    ExitQrNoActiveVehicle,
    ExitQrParkingLotNotFound,
    ExitQrProfileIncomplete,
    ExitQrUserInactive,
    ExitQrUserNotFound,
    request_exit_qr,
)
from app.services.exit_qr_service import (
    scan_exit_qr as process_exit_qr_scan,
)

router = APIRouter(
    prefix="/api/v1/parking-lots",
    tags=["Códigos QR"],
)


@router.post("/{parking_lot_id}/entry/qr")
def generate_entry_qr(
    parking_lot_id: str,
    current_user: CurrentUser,
):
    """Genera un QR temporal para solicitar el ingreso al campus."""

    try:
        return request_entry_qr(
            user_id=current_user["id"],
            parking_lot_id=parking_lot_id,
        )

    except EntryQrUserNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except EntryQrUserInactive as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except (
        EntryQrProfileIncomplete,
        EntryQrUserAlreadyInside,
        EntryQrParkingLotFull,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except EntryQrParkingLotNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except EntryQrDatabaseUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de generación de QR no está configurado correctamente",
        ) from exc


@router.post("/entry/qr/scan")
def scan_entry_qr_route(
    request: EntryQrScanRequest,
    current_user: CurrentUser,
):
    """Valida un QR de entrada y registra el ingreso del vehículo."""

    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permisos para operar como guardia",
        )

    try:
        return process_entry_qr_scan(
            request.qr_token.get_secret_value()
        )

    except EntryQrInvalidToken as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except EntryQrUserNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except EntryQrUserInactive as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except EntryQrParkingLotNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except EntryQrMovementConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except EntryQrDatabaseUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de validación de QR no está configurado correctamente",
        ) from exc


@router.post("/exit/qr")
def generate_exit_qr(
    current_user: CurrentUser,
):
    """Genera un QR temporal para solicitar el egreso del campus."""

    try:
        return request_exit_qr(
            user_id=current_user["id"],
        )

    except ExitQrUserNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ExitQrUserInactive as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except (
        ExitQrProfileIncomplete,
        ExitQrNoActiveVehicle,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except ExitQrParkingLotNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ExitQrDatabaseUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de generación de QR no está configurado correctamente",
        ) from exc


@router.post("/exit/qr/scan")
def scan_exit_qr_route(
    request: EntryQrScanRequest,
    current_user: CurrentUser,
):
    """Valida un QR de salida y registra el egreso del vehículo."""

    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permisos para operar como guardia",
        )

    try:
        return process_exit_qr_scan(
            request.qr_token.get_secret_value()
        )

    except ExitQrInvalidToken as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except ExitQrUserNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ExitQrUserInactive as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except ExitQrNoActiveVehicle as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except ExitQrParkingLotNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ExitQrMovementConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except ExitQrDatabaseUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de validación de QR no está configurado correctamente",
        ) from exc