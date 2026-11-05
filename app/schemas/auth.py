
from pydantic import BaseModel, SecretStr, field_validator


class LoginRequest(BaseModel):
    email: str
    password: SecretStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()

        if not value:
            raise ValueError("El correo electrónico es obligatorio")

        if "@" not in value:
            raise ValueError("Ingresá un correo electrónico válido")

        domain = value.rsplit("@", 1)[1]

        allowed_domains = {
            "unsam.edu.ar",
            "estudiantes.unsam.edu.ar",
            "unsam-bue.edu.ar",
        }

        if domain not in allowed_domains:
            raise ValueError(
                "Debés usar tu correo institucional de la UNSAM"
            )

        return value

class LoginUser(BaseModel):
    id: int
    full_name: str
    email: str
    role: str


class LoginResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"
    user: LoginUser
