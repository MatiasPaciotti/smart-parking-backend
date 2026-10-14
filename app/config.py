import os

from dotenv import load_dotenv

load_dotenv()


def get_cors_origins() -> list[str]:
    configured_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    )
    return [
        origin.strip() for origin in configured_origins.split(",") if origin.strip()
    ]
