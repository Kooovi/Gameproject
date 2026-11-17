"""Acceso a la base de datos SQLite.

Todo el SQL vive en archivos .sql (carpeta sql/), no mezclado con el Python.
Así cada consulta se puede leer, probar y explicar por separado.
"""

import sqlite3
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RUTA_DB = RAIZ / "data" / "costos.db"
CARPETA_SQL = RAIZ / "sql"
RUTA_ESQUEMA = Path(__file__).resolve().parent / "esquema.sql"


def conectar(ruta=None) -> sqlite3.Connection:
    """Abre la base (la crea si no existe) y se asegura de que tenga las tablas.

    Sin ruta usa RUTA_DB. Se lee al momento de llamar (y no como valor por defecto
    del parámetro) para que las pruebas puedan apuntar a una base temporal.
    """
    ruta = RUTA_DB if ruta is None else ruta
    if str(ruta) != ":memory:":
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta)
    # SQLite no revisa las llaves foráneas a menos que se le pida.
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(RUTA_ESQUEMA.read_text(encoding="utf-8"))
    return con


def texto_sql(nombre: str) -> str:
    """Devuelve el texto de sql/<nombre>.sql."""
    return (CARPETA_SQL / f"{nombre}.sql").read_text(encoding="utf-8")


def consulta(con: sqlite3.Connection, nombre: str, params=()) -> pd.DataFrame:
    """Ejecuta sql/<nombre>.sql y devuelve el resultado como DataFrame de pandas."""
    return pd.read_sql_query(texto_sql(nombre), con, params=params)


def hay_datos(con: sqlite3.Connection) -> bool:
    return con.execute("SELECT COUNT(*) FROM obras").fetchone()[0] > 0
