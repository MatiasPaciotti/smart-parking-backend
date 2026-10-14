import os

import psycopg


def get_database_connection() -> psycopg.Connection:
    required_settings = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
    if any(not os.getenv(name) for name in required_settings):
        raise ValueError("Falta configurar la conexión a PostgreSQL")

    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        sslmode=os.getenv("DB_SSLMODE", "require"),
        connect_timeout=5,
    )
