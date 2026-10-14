from fastapi import APIRouter, HTTPException, status

from app.schemas.user import UserRegistration, UserRegistrationResponse
from app.services.user_service import (
    DatabaseUnavailableError,
    DuplicateDataError,
    DuplicateEmailError,
    DuplicatePlateError,
    register_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["users"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserRegistrationResponse,
)
def register_user_route(registration: UserRegistration) -> UserRegistrationResponse:
    try:
        user = register_user(registration)
    except DuplicatePlateError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La patente ingresada ya se encuentra registrada",
        ) from error
    except DuplicateEmailError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo electrónico ya se encuentra registrado",
        ) from error
    except DuplicateDataError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Los datos ingresados ya se encuentran registrados",
        ) from error
    except DatabaseUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo conectar con la base de datos",
        ) from error

    return UserRegistrationResponse(
        message="Registro completado correctamente",
        user=user,
    )
