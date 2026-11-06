from pydantic import BaseModel, field_validator

from app.schemas.user import PLATE_PATTERN


def normalize_plate(value: str) -> str:
    """Normaliza la patente a mayúsculas sin espacios y valida su formato."""
    value = "".join(value.split()).upper()
    if not PLATE_PATTERN.fullmatch(value):
        raise ValueError("La patente debe tener formato AAA123 o AA123AA")
    return value


class GuestVehicleRequest(BaseModel):
    patente: str

    @field_validator("patente")
    @classmethod
    def validate_plate(cls, value: str) -> str:
        return normalize_plate(value)
