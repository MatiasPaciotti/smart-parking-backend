from pydantic import BaseModel, SecretStr, field_validator


class EntryQrScanRequest(BaseModel):
    qr_token: SecretStr

    @field_validator("qr_token")
    @classmethod
    def validate_qr_token(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("El token QR es obligatorio")

        return value