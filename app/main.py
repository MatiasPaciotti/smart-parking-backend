
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.users import router as users_router
from app.api.routes.protected import router as protected_router
from app.api.routes.parking_lots import router as parking_lots_router
from app.api.routes.occupancy import router as occupancy_router
from app.config import get_cors_origins

def create_app() -> FastAPI:
    application = FastAPI(
        title="Smart Parking API",
        description="API para la gestión de acceso a los estacionamientos del Campus Miguelete y Tornavías de la UNSAM",
        version="1.0.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(users_router)
    application.include_router(protected_router)
    application.include_router(parking_lots_router)
    application.include_router(occupancy_router)

    @application.get("/")
    def root():
        return {"message": "Smart Parking API funcionando"}

    return application


app = create_app()
