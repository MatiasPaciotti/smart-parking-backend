from pydantic import BaseModel, field_validator


class SelectParkingLotRequest(BaseModel):
    parking_lot_id: str

    @field_validator("parking_lot_id")
    @classmethod
    def normalize_parking_lot_id(cls, value: str) -> str:
        return value.strip().lower()