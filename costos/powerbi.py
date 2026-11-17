"""Exporta los datos en CSV listos para Power BI.

    python -m costos.powerbi             exporta los datos de ejemplo (ficticios)
    python -m costos.powerbi --actual    exporta lo que hay en data/costos.db

Genera, en la carpeta powerbi/datos/:
    obras.csv, partidas.csv, gastos.csv   las tablas de la base
    calendario.csv                        una fila por día (tabla de fechas)
    verificacion.csv                      los totales calculados con Python, para
                                          comprobar que tus medidas DAX dan lo mismo
"""

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

from costos import calculos, db, demo, importar

CARPETA = db.RAIZ / "powerbi" / "datos"

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def calendario(desde, hasta) -> pd.DataFrame:
    """Tabla de fechas: Power BI la necesita para agrupar por mes, trimestre, etc.

    Va de enero del primer año a diciembre del último, sin huecos: si un día no
    tuvo gastos, igual tiene que existir en el calendario.
    """
    dias = pd.date_range(f"{desde.year}-01-01", f"{hasta.year}-12-31", freq="D")
    return pd.DataFrame({
        "fecha": dias.strftime("%Y-%m-%d"),
        "anio": dias.year,
        "mes_num": dias.month,
        "mes": [MESES[m - 1] for m in dias.month],
        "anio_mes": dias.strftime("%Y-%m"),      # texto que se ordena bien: 2026-01, 2026-02...
        "trimestre": "T" + dias.quarter.astype(str),
    })


def tablas(con: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    obras = pd.read_sql_query(
        "SELECT id AS obra_id, codigo, nombre AS obra, cliente, fecha_inicio, fecha_fin_prevista "
        "FROM obras ORDER BY codigo", con)
    partidas = pd.read_sql_query(
        "SELECT id AS partida_id, obra_id, nombre AS partida, categoria, presupuesto, avance "
        "FROM partidas ORDER BY id", con)
    gastos = pd.read_sql_query(
        "SELECT id AS gasto_id, partida_id, fecha, proveedor, documento, descripcion, monto "
        "FROM gastos ORDER BY fecha, id", con)

    fechas = pd.to_datetime(gastos["fecha"])
    cal = calendario(fechas.min(), fechas.max()) if not fechas.empty else calendario(
        pd.Timestamp.today(), pd.Timestamp.today())

    # Lo que deberían dar las medidas DAX, calculado con el mismo código de la app.
    metricas = calculos.metricas_partidas(db.consulta(con, "resumen_partidas"))
    por_obra = calculos.resumen_obras(metricas)
    verificacion = por_obra[["obra_codigo", "presupuesto", "gastado", "costo_esperado",
                             "proyeccion", "sobrecosto_proyectado"]].copy()
    total = verificacion.drop(columns="obra_codigo").sum()
    verificacion.loc[len(verificacion)] = ["TOTAL", *total]
    verificacion[verificacion.columns[1:]] = verificacion[verificacion.columns[1:]].round(0)

    return {"obras": obras, "partidas": partidas, "gastos": gastos,
            "calendario": cal, "verificacion": verificacion}


def exportar(con: sqlite3.Connection, carpeta: Path = CARPETA) -> list[Path]:
    carpeta.mkdir(parents=True, exist_ok=True)
    rutas = []
    for nombre, df in tablas(con).items():
        ruta = carpeta / f"{nombre}.csv"
        # utf-8-sig agrega una marca al inicio para que Excel y Power BI
        # reconozcan las tildes sin preguntar la codificación.
        df.to_csv(ruta, index=False, encoding="utf-8-sig")
        rutas.append(ruta)
    return rutas


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta CSV para Power BI.")
    parser.add_argument("--actual", action="store_true", help="usar data/costos.db en vez del ejemplo")
    args = parser.parse_args()

    if args.actual:
        con = db.conectar()
    else:
        con = db.conectar(":memory:")
        limpios, _, _ = importar.validar(demo.generar())
        importar.cargar(con, limpios)

    for ruta in exportar(con):
        print(f"✔ {ruta.relative_to(db.RAIZ)}")


if __name__ == "__main__":
    main()
