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

### Rutas de la API

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/` | Confirma que la API está en ejecución. |
| `POST` | `/api/v1/auth/register` | Registra una cuenta no verificada y envía un código. |
| `POST` | `/api/v1/auth/verify-email` | Verifica el código enviado por correo. |
| `POST` | `/api/v1/auth/resend-verification` | Reenvía el código, hasta 3 veces por hora. |

### Detalles de validación

**Registro (`POST /api/v1/auth/register`)**

Campos requeridos: `nombre`, `apellido`, `email`, `patente`, `dni`, `password`

- **Email**: acepta dominios `@unsam.edu.ar`, `@estudiantes.unsam.edu.ar`, `@unsam-bue.edu.ar`
- **Contraseña**: entre 8 y 128 caracteres, almacenada con Argon2id y nunca devuelta en la respuesta
- **Patente**: formato `AAA123` o `AA123AA` (normaliza a mayúsculas y elimina espacios)
- **Nombre y apellido**: se guardan combinados en `full_name`
- **Rol**: asignado como `user` por defecto
- **Estado**: asignado como `active` y `email_verified = false`

**Código de verificación**

- Código de 6 dígitos
- Vence a los 10 minutos
- Almacenado hasheado
- Máximo 5 intentos fallidos antes de requerir un nuevo código
- Reenvío limitado a 3 veces por hora


