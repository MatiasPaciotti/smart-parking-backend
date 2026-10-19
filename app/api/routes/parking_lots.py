
from fastapi import APIRouter, HTTPException, status

router = APIRouter(
    prefix="/api/v1/parking-lots",
    tags=["Estacionamientos"],
)

PARKING_LOTS = {
    "tornavias": {
        "id": "tornavias",
        "name": "Tornavías",
    },
    "rodriguez-pena": {
        "id": "rodriguez-pena",
        "name": "Rodríguez Peña",
    },
}

DEFAULT_PARKING_LOT_ID = "rodriguez-pena"


@router.get("")
def list_parking_lots():
    """Devuelve los estacionamientos disponibles para seleccionar."""
    return {
        "parking_lots": list(PARKING_LOTS.values()),
        "default_parking_lot_id": DEFAULT_PARKING_LOT_ID,
    }


@router.get("/default")
def get_default_parking_lot(
    last_used_parking_lot_id: str | None = None,
):
    """Devuelve el último estacionamiento utilizado o el predeterminado inicial."""
    parking_lot_id = (
        last_used_parking_lot_id or DEFAULT_PARKING_LOT_ID
    )

    parking_lot = PARKING_LOTS.get(parking_lot_id)

    if parking_lot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El estacionamiento solicitado no existe",
        )

    return parking_lot


@router.get("/{parking_lot_id}")
def get_parking_lot(parking_lot_id: str):
    """Consulta un estacionamiento por su identificador."""
    parking_lot = PARKING_LOTS.get(parking_lot_id)

    if parking_lot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El estacionamiento solicitado no existe",
        )

    return parking_lot

