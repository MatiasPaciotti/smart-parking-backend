# Smart Parking Backend

Backend del sistema de gestión y control de acceso a los estacionamientos de los campus Miguelete y Tornavías de la Universidad Nacional de San Martín (UNSAM).

## Tecnologías

- Python 3
- FastAPI
- PostgreSQL
- Uvicorn

## Estructura

- `app/main.py`: crea la aplicación y registra los routers.
- `app/api/routes/`: endpoints HTTP y traducción de errores a respuestas.
- `app/schemas/`: validación de entradas y modelos de respuesta.
- `app/services/`: reglas del dominio y coordinación de operaciones.
- `app/repositories/`: consultas y persistencia en PostgreSQL.
- `app/database.py` y `app/config.py`: conexión y configuración.

## Requisitos

- Python 3.10 o superior
- Git

La ruta de registro requiere una instancia PostgreSQL accesible.

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
| `POST` | `/api/v1/auth/register` | Registra una persona y su patente. |

El endpoint recibe `nombre`, `apellido`, `email`, `patente`, `dni` y `password`.
La contraseña debe tener entre 8 y 128 caracteres; se almacena usando Argon2id y
nunca se devuelve en la respuesta. Acepta únicamente
correos de `@unsam.edu.ar` o `@estudiantes.unsam.edu.ar`; normaliza la patente a
mayúsculas y elimina espacios antes de validar formatos `AAA123` y `AA123AA`.
Responde `201` al crear el usuario y `409` si el correo o la patente ya existen.
La patente duplicada devuelve el detalle `La patente ingresada ya se encuentra
registrada`. El nombre y apellido se guardan combinados en `full_name`; el rol
se asigna como `user`, el estado como `active` y el usuario comienza fuera del
campus. La respuesta sigue los campos de la tabla `user`. El frontend debe redirigir al dashboard tras un
`201`; este repositorio contiene únicamente el backend.

La aplicación carga las variables de `.env` automáticamente. Configurá
`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`; `DB_SSLMODE` es
opcional y por defecto usa `require`. El registro persiste en la tabla existente
`user`; el `dni`, el correo y la patente deben ser únicos según las restricciones
de PostgreSQL.

## Configuración

Por defecto, CORS permite peticiones desde `localhost` y `127.0.0.1` en los puertos `5173` y `3000`. Para usar otros orígenes, definí `CORS_ORIGINS` como una lista separada por comas antes de iniciar el servidor, por ejemplo:

```bash
export CORS_ORIGINS="https://frontend.example.com,http://localhost:5173"
uvicorn app.main:app --reload
```

Incluí el esquema y el puerto de cada origen cuando corresponda. La aplicación carga `.env` al iniciar; las variables ya definidas en el entorno del proceso tienen prioridad.

El archivo `.env` está excluido de Git. Usá `.env.example` como referencia y
no subas credenciales reales al repositorio.

## Estado del proyecto

La API incluye el registro inicial de usuarios. La autenticación y las demás
rutas del dominio de estacionamiento todavía están pendientes.