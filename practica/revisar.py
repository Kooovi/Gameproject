"""Revisor de la práctica de SQL.

    python practica/revisar.py        revisa todos los ejercicios
    python practica/revisar.py 7      muestra lo que devuelve tu consulta del ejercicio 7

Corre tus consultas de practica/ejercicios.sql y las de practica/soluciones.sql
sobre la misma base (los datos de ejemplo) y compara los RESULTADOS, no el texto:
cualquier consulta que devuelva lo correcto vale, aunque esté escrita distinto.
"""

import re
import sqlite3
import sys
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA.parent))        # para poder importar el paquete costos

from costos import db, demo, importar          # noqa: E402  (va después de ajustar la ruta)

RUTA_DB = CARPETA.parent / "data" / "practica.db"
ENCABEZADO = re.compile(r"^-- \[(\d+)\]\s*(.*)$")


def leer_ejercicios(ruta: Path) -> dict[int, dict]:
    """Parte el archivo en ejercicios. Cada uno empieza con una línea '-- [n] enunciado'."""
    ejercicios, actual = {}, None
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        coincide = ENCABEZADO.match(linea)
        if coincide:
            actual = int(coincide.group(1))
            ejercicios[actual] = {"enunciado": coincide.group(2), "sql": []}
        elif actual is not None and not linea.strip().startswith("--"):
            ejercicios[actual]["sql"].append(linea)
    for e in ejercicios.values():
        e["sql"] = "\n".join(e["sql"]).strip()
    return ejercicios


def preparar_base() -> sqlite3.Connection:
    """Crea data/practica.db desde cero con los datos de ejemplo."""
    RUTA_DB.unlink(missing_ok=True)
    con = db.conectar(RUTA_DB)
    limpios, _, _ = importar.validar(demo.generar())
    importar.cargar(con, limpios)
    return con


def normalizar(filas: list[tuple]) -> list[tuple]:
    """Redondea los decimales para que 0.1 + 0.2 y 0.3 cuenten como iguales."""
    return [tuple(round(v, 2) if isinstance(v, float) else v for v in fila) for fila in filas]


def comparar(mias: list[tuple], esperadas: list[tuple], importa_orden: bool) -> str | None:
    """Devuelve None si está bien, o una pista de qué anda mal."""
    if mias and esperadas and len(mias[0]) != len(esperadas[0]):
        return f"devuelve {len(mias[0])} columna(s) y se esperaban {len(esperadas[0])}"
    if len(mias) != len(esperadas):
        return f"devuelve {len(mias)} fila(s) y se esperaban {len(esperadas)}"
    if mias == esperadas:
        return None
    # Para comparar sin importar el orden se ordenan las dos listas igual (como texto,
    # porque Python no sabe ordenar un None contra un número).
    if sorted(mias, key=repr) == sorted(esperadas, key=repr):
        return "las filas son las correctas, pero en otro orden" if importa_orden else None
    for i, (mia, esperada) in enumerate(zip(mias, esperadas), start=1):
        if mia != esperada:
            return f"la fila {i} no coincide: tu consulta da {mia}"
    return "el resultado no coincide"


def mostrar(con: sqlite3.Connection, sql: str, maximo: int = 15) -> None:
    cursor = con.execute(sql)
    print(" | ".join(columna[0] for columna in cursor.description))
    filas = cursor.fetchall()
    for fila in filas[:maximo]:
        print(" | ".join("NULL" if v is None else str(v) for v in fila))
    if len(filas) > maximo:
        print(f"... y {len(filas) - maximo} fila(s) más")
    print(f"({len(filas)} filas)")


def main() -> None:
    mios = leer_ejercicios(CARPETA / "ejercicios.sql")
    soluciones = leer_ejercicios(CARPETA / "soluciones.sql")
    con = preparar_base()

    if len(sys.argv) > 1:                       # modo "mostrame mi resultado"
        numero = int(sys.argv[1])
        if not mios.get(numero, {}).get("sql"):
            print(f"El ejercicio {numero} todavía no tiene consulta.")
            return
        mostrar(con, mios[numero]["sql"])
        return

    buenos = 0
    for numero, solucion in sorted(soluciones.items()):
        sql = mios.get(numero, {}).get("sql", "")
        if not sql:
            print(f"⏳ {numero:>2}  pendiente")
            continue
        try:
            mias = normalizar(con.execute(sql).fetchall())
        except sqlite3.Error as error:          # error de sintaxis, tabla que no existe, etc.
            print(f"❌ {numero:>2}  error de SQL: {error}")
            continue
        esperadas = normalizar(con.execute(solucion["sql"]).fetchall())
        pista = comparar(mias, esperadas, importa_orden="Ordená" in solucion["enunciado"])
        if pista is None:
            buenos += 1
            print(f"✅ {numero:>2}  correcto")
        else:
            print(f"❌ {numero:>2}  {pista}")

    print(f"\n{buenos} de {len(soluciones)} correctos.")
    print(f"Base para explorar a mano:  sqlite3 {RUTA_DB.relative_to(CARPETA.parent)}")


if __name__ == "__main__":
    main()
