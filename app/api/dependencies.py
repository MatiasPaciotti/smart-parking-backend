
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.security.tokens import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> dict:
    """Obtiene al usuario autenticado a partir de un JWT válido."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o vencido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "id": int(payload["sub"]),
        "email": payload["email"],
        "role": payload["role"],
        "parking_lot_id": payload.get("parking_lot_id"),
    }


CurrentUser = Annotated[dict, Depends(get_current_user)]


def get_current_guardia(current_user: CurrentUser) -> dict:
    """Valida que el usuario pueda operar y tenga una garita seleccionada."""

    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permisos para operar como guardia",
        )

    parking_lot_id = current_user.get("parking_lot_id")

    if not parking_lot_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Primero tenés que seleccionar una garita",
        )

    return current_user


CurrentGuardia = Annotated[dict, Depends(get_current_guardia)]


def get_guardia_for_selected_parking_lot(
    parking_lot_id: str,
    current_guardia: CurrentGuardia,
) -> dict:
    """Rechaza operaciones dirigidas a una garita distinta de la activa."""

    if parking_lot_id != current_guardia["parking_lot_id"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La garita solicitada no coincide con la garita activa",
        )

    return current_guardia


CurrentGuardiaForParkingLot = Annotated[
    dict,
    Depends(get_guardia_for_selected_parking_lot),
]