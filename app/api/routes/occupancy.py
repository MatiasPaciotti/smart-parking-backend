
from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentGuardiaForParkingLot
from app.repositories.occupancy_repository import get_parking_occupancy

router = APIRouter(
    prefix="/api/v1/parking-lots",
    tags=["Ocupación"],
)


@router.get("/{parking_lot_id}/occupancy")
def get_occupancy(
    parking_lot_id: str,
    current_guardia: CurrentGuardiaForParkingLot,
):
    """Devuelve la ocupación actual del estacionamiento solicitado."""

    try:
        occupancy = get_parking_occupancy(parking_lot_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if occupancy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El estacionamiento solicitado no existe",
        )

    return occupancy
