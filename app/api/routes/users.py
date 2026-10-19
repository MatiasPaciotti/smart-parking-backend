
from fastapi import APIRouter, HTTPException, status

from app.schemas.user import (
    MessageResponse,
    ResendVerificationRequest,
    UserRegistration,
    UserRegistrationResponse,
    VerifyEmailRequest,
)
from app.services.email_service import EmailDeliveryError, enviar_codigo_verificacion
from app.services.user_service import (
    DatabaseUnavailableError,
    DuplicateDataError,
    DuplicateEmailError,
    DuplicatePlateError,
    register_user,
    resend_email_code,
    verify_email_code,
)

from app.schemas.auth import LoginRequest, LoginResponse, LoginUser
from app.security.tokens import create_access_token
from app.services.auth_service import (
    InvalidCredentialsError,
    authenticate_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["users"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserRegistrationResponse,
)
def register_user_route(registration: UserRegistration) -> UserRegistrationResponse:
    try:
        user, code = register_user(registration)
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

    try:
        enviar_codigo_verificacion(registration.email, code)
    except EmailDeliveryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "La cuenta quedó creada sin verificar, pero no se pudo enviar el "
                "código. Podés solicitar un reenvío."
            ),
        ) from error

    return UserRegistrationResponse(
        message="Cuenta creada. Revisá tu correo para verificarla.",
        user=user,
    )



@router.post("/login", response_model=LoginResponse)
def login_route(credentials: LoginRequest) -> LoginResponse:
    try:
        user = authenticate_user(
            email=credentials.email,
            password=credentials.password.get_secret_value(),
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos",
        ) from error
    except DatabaseUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo consultar la base de datos",
        ) from error

    try:
        access_token = create_access_token(
            user_id=user["id"],
            email=user["email"],
            role=user["role"],
        )
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de autenticación no está configurado correctamente",
        ) from error

    return LoginResponse(
        message="Inicio de sesión exitoso",
        access_token=access_token,
        token_type="bearer",
        user=LoginUser(
            id=user["id"],
            full_name=user["full_name"],
            email=user["email"],
            role=user["role"],
        ),
    )

@router.post(
    "/verify-email",
    response_model=MessageResponse,
)
def verify_email_route(request: VerifyEmailRequest) -> MessageResponse:
    try:
        verified = verify_email_code(request.email, request.code)
    except DatabaseUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo verificar el código en este momento",
        ) from error

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código es inválido, venció o alcanzó el límite de intentos",
        )

    return MessageResponse(message="Correo verificado correctamente")


@router.post(
    "/resend-verification",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MessageResponse,
)
def resend_verification_route(
    request: ResendVerificationRequest,
) -> MessageResponse:
    try:
        should_send, code = resend_email_code(request.email)
    except DatabaseUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo procesar el reenvío en este momento",
        ) from error

    if should_send:
        try:
            enviar_codigo_verificacion(request.email, code)
        except EmailDeliveryError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo enviar el código. Intentá nuevamente más tarde.",
            ) from error

    return MessageResponse(
        message="Si la cuenta existe y no está verificada, recibirás un código por correo."
    )
