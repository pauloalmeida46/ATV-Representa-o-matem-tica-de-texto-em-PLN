"""Configuracao de acesso ao PostgreSQL, lida do ambiente ou do arquivo .env."""

import os

from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "5432")),
    "user": os.getenv("PGUSER", "postgres"),
    "password": os.getenv("PGPASSWORD", ""),
    "database": os.getenv("PGDATABASE", "pc7_pessoas"),
}
