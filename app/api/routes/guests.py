from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import AdminUser
from app.repositories.guest_repository import (
    GuestParkingLotNotFound,
    GuestVehicleConflict,
    GuestVehicleNotFound,
)
from app.schemas.guest import GuestVehicleRequest, normalize_plate
from app.services.guest_service import (
    DatabaseUnavailableError,
    list_guest_vehicles,
    register_guest_vehicle,
    remove_guest_vehicle,
)

router = APIRouter(
    prefix="/api/v1/admin/parking-lots",
    tags=["Invitados"],
)


@router.post(
    "/{parking_lot_id}/guests",
    status_code=status.HTTP_201_CREATED,
)
def register_guest_vehicle_route(
    parking_lot_id: str,
    request: GuestVehicleRequest,
    current_admin: AdminUser,
):
    """Registra el vehículo de un invitado en el estacionamiento."""

    try:
        result = register_guest_vehicle(
            plate=request.patente,
            created_by=current_admin["id"],
            parking_lot_id=parking_lot_id,
        )
    except GuestParkingLotNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except GuestVehicleConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except DatabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo registrar el vehículo del invitado",
        ) from exc

    return {
        "message": "Vehículo de invitado registrado correctamente",
        **result,
    }


@router.delete("/{parking_lot_id}/guests/{patente}")
def remove_guest_vehicle_route(
    parking_lot_id: str,
    patente: str,
    current_admin: AdminUser,
):
    """Quita el vehículo de un invitado del estacionamiento."""

    try:
        plate = normalize_plate(patente)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    try:
        result = remove_guest_vehicle(
            plate=plate,
            parking_lot_id=parking_lot_id,
        )
    except GuestParkingLotNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except GuestVehicleNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo quitar el vehículo del invitado",
        ) from exc

    return {
        "message": "Vehículo de invitado quitado correctamente",
        **result,
    }


@router.get("/{parking_lot_id}/guests")
def list_guest_vehicles_route(
    parking_lot_id: str,
    current_admin: AdminUser,
):
    """Lista los vehículos de invitados estacionados en el estacionamiento."""

    try:
        guests = list_guest_vehicles(parking_lot_id=parking_lot_id)
    except GuestParkingLotNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DatabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo consultar los vehículos de invitados",
        ) from exc

    return {
        "parking_lot_id": parking_lot_id,
        "guests": guests,
    }
