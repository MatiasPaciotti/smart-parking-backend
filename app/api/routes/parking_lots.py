
from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentGuardia, CurrentUser
from app.schemas.parking_lot import SelectParkingLotRequest
from app.security.tokens import create_access_token

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


@router.get("/active")
def get_active_parking_lot(current_user: CurrentGuardia):
    """Devuelve la garita activa del guardia autenticado."""

    parking_lot = PARKING_LOTS.get(current_user["parking_lot_id"])

    if parking_lot is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La garita activa no es válida. Seleccioná una garita nuevamente.",
        )

    return {"parking_lot": parking_lot}


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


@router.post("/select")
def select_parking_lot(
    request: SelectParkingLotRequest,
    current_user: CurrentUser,
):
    """Selecciona o cambia la garita activa del guardia."""

    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permisos para seleccionar una garita operativa",
        )

    parking_lot = PARKING_LOTS.get(request.parking_lot_id)

    if parking_lot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El estacionamiento solicitado no existe",
        )

    try:
        access_token = create_access_token(
            user_id=current_user["id"],
            email=current_user["email"],
            role=current_user["role"],
            parking_lot_id=parking_lot["id"],
        )
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de autenticación no está configurado correctamente",
        ) from error

    return {
        "message": "Garita seleccionada correctamente",
        "access_token": access_token,
        "token_type": "bearer",
        "parking_lot": parking_lot,
    }