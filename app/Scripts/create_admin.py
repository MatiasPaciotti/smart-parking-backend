"""Crea o actualiza un usuario con rol de administrador en la tabla "user".

Se ejecuta desde la raíz del backend, con el entorno virtual activado:

    python -m scripts.create_admin --email admin@unsam.edu.ar

La contraseña se pide por consola sin mostrarla. Para correrlo sin interacción
se puede definir la variable de entorno ADMIN_PASSWORD (también se lee del .env).

La contraseña se guarda con Argon2id, igual que en el registro de usuarios, y
nunca se imprime. Si el correo ya existe, se le asigna el rol de administrador
y se reemplaza su contraseña.
"""

import argparse
import getpass
import os
import re
import sys

import psycopg
from dotenv import load_dotenv

from app.database import get_database_connection
from app.security.passwords import hash_password

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DEFAULT_ROLE = "admin"
DEFAULT_FULL_NAME = "Administrador"
COLUMN_FLAGS = {"plate": "--plate", "dni": "--dni"}


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Crea (o actualiza) un usuario administrador en la tabla "user".'
    )
    parser.add_argument("--email", required=True, help="Correo con el que iniciará sesión")
    parser.add_argument(
        "--full-name",
        default=DEFAULT_FULL_NAME,
        help=f"Nombre completo (por defecto: {DEFAULT_FULL_NAME})",
    )
    parser.add_argument(
        "--role",
        default=DEFAULT_ROLE,
        help=f"Valor de la columna role (por defecto: {DEFAULT_ROLE})",
    )
    parser.add_argument(
        "--plate",
        help="Patente. Solo hace falta si la columna no admite NULL",
    )
    parser.add_argument(
        "--dni",
        type=int,
        help="DNI. Solo hace falta si la columna no admite NULL",
    )
    return parser.parse_args()


def read_password() -> str:
    password = os.getenv("ADMIN_PASSWORD")
    if password is None:
        password = getpass.getpass("Contraseña del administrador: ")
        if password != getpass.getpass("Repetí la contraseña: "):
            fail("Las contraseñas no coinciden")
    if not 8 <= len(password) <= 128:
        fail("La contraseña debe tener entre 8 y 128 caracteres")
    return password


def save_admin(
    *,
    email: str,
    password_hash: str,
    full_name: str,
    role: str,
    plate: str | None,
    dni: int | None,
) -> tuple[int, bool]:
    """Devuelve (id, creado). `creado` es False si el usuario ya existía."""
    with get_database_connection() as connection:
        existing = connection.execute(
            'SELECT id FROM "user" WHERE email = %s', (email,)
        ).fetchone()

        if existing:
            connection.execute(
                """
                UPDATE "user"
                SET role = %s, account_status = %s, password_hash = %s
                WHERE id = %s
                """,
                (role, "active", password_hash, existing[0]),
            )
            return existing[0], False

        row = connection.execute(
            """
            INSERT INTO "user" (
                full_name, email, role, account_status,
                is_on_campus, plate, dni, password_hash
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (full_name, email, role, "active", False, plate, dni, password_hash),
        ).fetchone()
        return row[0], True


def main() -> None:
    load_dotenv()
    args = parse_args()

    email = args.email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        fail("El correo electrónico no es válido")

    full_name = args.full_name.strip()
    if not full_name:
        fail("El nombre completo no puede estar vacío")

    plate = "".join(args.plate.split()).upper() if args.plate else None
    password_hash = hash_password(read_password())

    try:
        user_id, created = save_admin(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=args.role,
            plate=plate,
            dni=args.dni,
        )
    except ValueError as error:
        fail(str(error))
    except psycopg.errors.NotNullViolation as error:
        column = error.diag.column_name
        flag = COLUMN_FLAGS.get(column)
        hint = f" Pasalo con {flag}." if flag else ""
        fail(f"La tabla exige un valor para la columna '{column}'.{hint}")
    except psycopg.errors.UniqueViolation as error:
        fail(
            "Ya existe otro usuario con esos datos "
            f"(restricción '{error.diag.constraint_name}')"
        )
    except (psycopg.errors.CheckViolation, psycopg.errors.InvalidTextRepresentation) as error:
        fail(
            f"La base no aceptó el rol '{args.role}': {error.diag.message_primary}. "
            "Revisá qué valores admite la columna role y pasalo con --role."
        )
    except psycopg.OperationalError:
        fail("No se pudo conectar con la base de datos. Revisá el .env")
    except psycopg.Error as error:
        fail(f"Error de base de datos: {error}")

    action = "creado" if created else "actualizado (ya existía; se reemplazó su contraseña)"
    print(f"Usuario administrador {action}")
    print(f"  id:    {user_id}")
    print(f"  email: {email}")
    print(f"  rol:   {args.role}")


if __name__ == "__main__":
    main()
