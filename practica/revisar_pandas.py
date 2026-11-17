"""Revisor de la práctica de pandas.

    python practica/revisar_pandas.py        revisa todos los ejercicios
    python practica/revisar_pandas.py 4      muestra lo que devuelve tu función ej4

Llama a tus funciones de practica/pandas_ejercicios.py y a las de
practica/pandas_soluciones.py con los mismos datos, y compara lo que devuelven.
"""

import sys
from pathlib import Path

import pandas as pd

CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA.parent))
sys.path.insert(0, str(CARPETA))

import pandas_ejercicios as mios               # noqa: E402
import pandas_soluciones as soluciones         # noqa: E402
from costos import db, demo, importar          # noqa: E402

TOTAL = 12


def cargar_tablas() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Las tres tablas de la base como DataFrames, con las fechas ya convertidas."""
    con = db.conectar(":memory:")
    limpios, _, _ = importar.validar(demo.generar())
    importar.cargar(con, limpios)
    obras = pd.read_sql_query("SELECT * FROM obras", con, parse_dates=["fecha_inicio", "fecha_fin_prevista"])
    partidas = pd.read_sql_query("SELECT * FROM partidas", con)
    gastos = pd.read_sql_query("SELECT * FROM gastos", con, parse_dates=["fecha"])
    return obras, partidas, gastos


def _valor(v):
    """Deja los valores comparables: redondea, y unifica vacíos y fechas."""
    if pd.isna(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, (int, float)) or hasattr(v, "item"):      # incluye los números de numpy
        return round(float(v), 2)
    return v


def a_filas(resultado, columnas: list[str]):
    """Convierte un DataFrame en lista de filas. Devuelve (filas, problema)."""
    if isinstance(resultado, pd.Series):
        resultado = resultado.reset_index()
    if not isinstance(resultado, pd.DataFrame):
        return None, f"se esperaba un DataFrame y devolviste {type(resultado).__name__}"
    if not set(columnas) <= set(resultado.columns):
        resultado = resultado.reset_index()      # por si las columnas quedaron en el índice
    faltan = [c for c in columnas if c not in resultado.columns]
    if faltan:
        return None, f"faltan las columnas: {', '.join(faltan)}"
    filas = [tuple(_valor(v) for v in fila) for fila in resultado[columnas].itertuples(index=False)]
    return filas, None


def comparar(mio, esperado) -> str | None:
    """Devuelve None si está bien, o una pista."""
    if not isinstance(esperado, (pd.DataFrame, pd.Series)):       # la respuesta es un número
        try:
            return None if round(float(mio), 2) == round(float(esperado), 2) else "el número no coincide"
        except (TypeError, ValueError):
            return f"se esperaba un número y devolviste {type(mio).__name__}"

    columnas = [str(c) for c in esperado.reset_index().columns if c != "index"]
    esperadas, _ = a_filas(esperado, columnas)
    mias, problema = a_filas(mio, columnas)
    if problema:
        return problema
    if len(mias) != len(esperadas):
        return f"devuelve {len(mias)} fila(s) y se esperaban {len(esperadas)}"
    if mias == esperadas:
        return None
    if sorted(mias, key=repr) == sorted(esperadas, key=repr):
        return "las filas son las correctas, pero en otro orden"
    for i, (mia, esperada) in enumerate(zip(mias, esperadas), start=1):
        if mia != esperada:
            return f"la fila {i} no coincide: tu función da {mia}"


def main() -> None:
    tablas = cargar_tablas()

    if len(sys.argv) > 1:
        # .copy() para que una función no pueda modificar las tablas originales.
        print(getattr(mios, f"ej{sys.argv[1]}")(*(t.copy() for t in tablas)))
        return

    buenos = 0
    for numero in range(1, TOTAL + 1):
        try:
            mio = getattr(mios, f"ej{numero}")(*(t.copy() for t in tablas))
        except Exception as error:               # cualquier error dentro de tu función
            print(f"❌ {numero:>2}  error: {type(error).__name__}: {error}")
            continue
        if mio is None:
            print(f"⏳ {numero:>2}  pendiente")
            continue
        esperado = getattr(soluciones, f"ej{numero}")(*(t.copy() for t in tablas))
        pista = comparar(mio, esperado)
        if pista is None:
            buenos += 1
            print(f"✅ {numero:>2}  correcto")
        else:
            print(f"❌ {numero:>2}  {pista}")
    print(f"\n{buenos} de {TOTAL} correctos.")


if __name__ == "__main__":
    main()
