
from pydantic import BaseModel, EmailStr, Field, field_validator


class EmailVerificationRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        domain = value.rsplit("@", 1)[-1]

        allowed_domains = {
            "unsam.edu.ar",
            "estudiantes.unsam.edu.ar",
        }

        if domain not in allowed_domains:
            raise ValueError(
                "Debés usar tu correo institucional de la UNSAM"
            )

        return value


class ConfirmEmailVerificationRequest(EmailVerificationRequest):
    code: str = Field(pattern=r"^[0-9]{6}$")


class EmailVerificationResponse(BaseModel):
    message: str
