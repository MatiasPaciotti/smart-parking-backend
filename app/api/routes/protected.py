import psycopg
from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser
from app.repositories.campus_status_repository import (
    get_campus_status_by_user_id,
)
from app.repositories.user_repository import get_user_profile_by_id

router = APIRouter(
    prefix="/api/v1",
    tags=["Autenticación"],
)


@router.get("/auth/me")
def get_authenticated_user(current_user: CurrentUser):
    """Devuelve los datos básicos del usuario autenticado."""
    return {
        "message": "Autenticación correcta",
        "user": current_user,
    }


@router.get("/auth/profile")
def get_authenticated_profile(current_user: CurrentUser):
    """Devuelve el perfil del usuario autenticado."""
    try:
        profile = get_user_profile_by_id(current_user["id"])
    except psycopg.Error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo consultar el perfil",
        )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el usuario",
        )

    if profile["account_status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta no está activa",
        )

    return profile


@router.get("/auth/campus-status")
def get_authenticated_campus_status(current_user: CurrentUser):
    """Devuelve el estado de presencia del usuario autenticado."""

    try:
        campus_status = get_campus_status_by_user_id(
            current_user["id"]
        )
    except psycopg.Error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo consultar el estado del campus",
        )

    if campus_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el usuario",
        )

    if campus_status["account_status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta no está activa",
        )

    return {
        "is_on_campus": campus_status["is_on_campus"],
    }