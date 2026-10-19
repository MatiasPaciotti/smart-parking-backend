import re

from pydantic import BaseModel, Field, SecretStr, field_validator

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"(?:unsam\.edu\.ar|estudiantes\.unsam\.edu\.ar|unsam-bue\.edu\.ar|gmail\.com)$",
    re.IGNORECASE,
)
PLATE_PATTERN = re.compile(r"^(?:[A-Z]{3}[0-9]{3}|[A-Z]{2}[0-9]{3}[A-Z]{2})$")


class UserRegistration(BaseModel):
    nombre: str
    apellido: str
    email: str
    patente: str
    dni: int = Field(gt=0, le=9_223_372_036_854_775_807)
    password: SecretStr

    @field_validator("nombre", "apellido")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Este campo es obligatorio")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if not 8 <= len(password) <= 128:
            raise ValueError("La contraseña debe tener entre 8 y 128 caracteres")
        return value

    @field_validator("email")
    @classmethod
    def validate_institutional_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError(
                "Ingresá un correo válido de @unsam.edu.ar, @estudiantes.unsam.edu.ar, @unsam-bue.edu.ar o @gmail.com"
            )
        local_part = value.split("@", maxsplit=1)[0]
        if ".." in local_part or local_part.startswith(".") or local_part.endswith("."):
            raise ValueError("Ingresá un correo electrónico válido")
        return value

    @field_validator("patente")
    @classmethod
    def normalize_and_validate_plate(cls, value: str) -> str:
        value = "".join(value.split()).upper()
        if not PLATE_PATTERN.fullmatch(value):
            raise ValueError("La patente debe tener formato AAA123 o AA123AA")
        return value


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    account_status: str
    is_on_campus: bool
    plate: str
    dni: int
    email_verified: bool


class UserRegistrationResponse(BaseModel):
    message: str
    user: UserResponse


class VerifyEmailRequest(BaseModel):
    email: str
    code: str = Field(pattern=r"^[0-9]{6}$")


class ResendVerificationRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_institutional_email(cls, value: str) -> str:
        return UserRegistration.validate_institutional_email(value)


class MessageResponse(BaseModel):
    message: str
