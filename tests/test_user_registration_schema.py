import pytest
from pydantic import ValidationError

from app.schemas.user import UserRegistration


@pytest.mark.parametrize(
    "email",
    [
        "usuario@unsam.edu.ar",
        "usuario@estudiantes.unsam.edu.ar",
        "usuario@unsam-bue.edu.ar",
    ],
)
def test_registration_accepts_institutional_emails(email):
    user = UserRegistration(
        nombre="Usuario",
        apellido="Prueba",
        email=email,
        patente="ABC123",
        dni=12345678,
        password="Password123",
    )

    assert user.email == email


@pytest.mark.parametrize(
    "email",
    [
        "usuario@gmail.com",
        "usuario@yahoo.com",
    ],
)
def test_registration_rejects_non_institutional_emails(email):
    with pytest.raises(ValidationError):
        UserRegistration(
            nombre="Usuario",
            apellido="Prueba",
            email=email,
            patente="ABC123",
            dni=12345678,
            password="Password123",
        )