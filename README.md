# Smart Parking Backend

Backend del sistema de gestión y control de acceso a los estacionamientos de los campus Miguelete y Tornavías de la Universidad Nacional de San Martín (UNSAM).

## Tecnologías

- Python 3
- FastAPI
- PostgreSQL
- Uvicorn

## Requisitos

- Python 3.10 o superior
- Git

PostgreSQL no es necesario para ejecutar la ruta de prueba actual.

## Instalación y ejecución

Cloná el repositorio y entrá en el directorio:

```bash
git clone <URL_DEL_REPOSITORIO>
cd smart-parking-backend
```

Creá y activá un entorno virtual, e instalá las dependencias:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Iniciá el servidor de desarrollo desde la raíz del proyecto:

```bash
uvicorn app.main:app --reload
```

La API queda disponible en <http://127.0.0.1:8000>. La documentación interactiva de Swagger está en <http://127.0.0.1:8000/docs> y la documentación ReDoc en <http://127.0.0.1:8000/redoc>.

## Rutas disponibles

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/` | Confirma que la API está en ejecución. |

## Configuración

Por defecto, CORS permite peticiones desde `localhost` y `127.0.0.1` en los puertos `5173` y `3000`. Para usar otros orígenes, definí `CORS_ORIGINS` como una lista separada por comas antes de iniciar el servidor, por ejemplo:

```bash
export CORS_ORIGINS="https://frontend.example.com,http://localhost:5173"
uvicorn app.main:app --reload
```

Incluí el esquema y el puerto de cada origen cuando corresponda. La aplicación lee esta variable del entorno del proceso, no del archivo `.env`.

El archivo `.env` está excluido de Git. Aunque el entorno local puede contener variables `DB_*`, la aplicación todavía no las carga ni abre conexiones a PostgreSQL. Cuando se incorpore la configuración de base de datos, agregá un `.env.example` con los nombres de las variables necesarias y documentá su uso aquí; no subas credenciales reales al repositorio.

## Estado del proyecto

Esta es una base inicial: por ahora expone una única ruta de comprobación. La integración con PostgreSQL, las rutas del dominio de estacionamiento y sus pruebas todavía están pendientes.