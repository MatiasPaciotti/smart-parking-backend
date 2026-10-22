
from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentGuardiaForParkingLot
from app.repositories.parking_movement_repository import (
    ParkingLotNotFound,
    ParkingMovementConflict,
    register_entry,
    register_exit,
)

router = APIRouter(
    prefix="/api/v1/parking-lots",
    tags=["Movimientos de estacionamiento"],
)


def handle_movement_error(exc: Exception) -> None:
    if isinstance(exc, ParkingLotNotFound):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if isinstance(exc, ParkingMovementConflict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    raise exc


@router.post("/{parking_lot_id}/entry")
def enter_parking_lot(
    parking_lot_id: str,
    current_user: CurrentGuardiaForParkingLot,
):
    """Registra el ingreso del usuario autenticado a un estacionamiento."""

    try:
        movement = register_entry(
            user_id=current_user["id"],
            parking_lot_id=parking_lot_id,
        )
    except (ParkingLotNotFound, ParkingMovementConflict) as exc:
        handle_movement_error(exc)

    return {
        "message": "Ingreso registrado correctamente",
        **movement,
    }


@router.post("/{parking_lot_id}/exit")
def exit_parking_lot(
    parking_lot_id: str,
    current_user: CurrentGuardiaForParkingLot,
):
    """Registra el egreso del usuario autenticado del estacionamiento."""

    try:
        movement = register_exit(
            user_id=current_user["id"],
            parking_lot_id=parking_lot_id,
        )
    except (ParkingLotNotFound, ParkingMovementConflict) as exc:
        handle_movement_error(exc)

    return {
        "message": "Egreso registrado correctamente",
        **movement,
    }
