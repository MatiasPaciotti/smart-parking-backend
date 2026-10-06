from fastapi import FastAPI

app = FastAPI(
    title="Smart Parking API",
    description="API para la gestión de acceso a los estacionamientos del Campus Miguelete y Tornavías de la UNSAM",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "Smart Parking API funcionando - Probando mi rama"
    }