"""Resumen corto de alertas, listo para pegar en WhatsApp o en un correo.

    python -m costos.alertas                  con los datos de ejemplo (ficticios)
    python -m costos.alertas --actual         con lo que hay en data/costos.db
    python -m costos.alertas --tolerancia 5   cambia la tolerancia del semáforo (en %)

Es el primer paso de automatizar: en vez de abrir la app para ver si algo va mal,
un script arma el resumen solo. Ver docs/AUTOMATIZAR.md para programarlo.
"""

import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from costos import calculos, db, demo, importar

ORDEN = {calculos.SOBRECOSTO: 0, calculos.EN_RIESGO: 1, calculos.EN_PRESUPUESTO: 2}


def millones(x: float) -> str:
    """78000000 -> '₡78,0 M'. En un mensaje corto se leen mejor los millones."""
    signo = "-" if x < 0 else ""
    # Formato de Costa Rica: espacio para los miles y coma para los decimales.
    texto = f"{abs(x) / 1_000_000:,.1f}".replace(",", " ").replace(".", ",")
    return f"{signo}₡{texto} M"


def resumen(partidas: pd.DataFrame, obras: pd.DataFrame, fecha: str, max_partidas: int = 3) -> str:
    """Arma el texto. Recibe las tablas que ya devuelven las funciones de calculos.py."""
    lineas = [f"*Control de costos · {fecha}*", ""]

    # Las obras con problemas primero: rojo, después amarillo, después verde.
    obras = obras.assign(orden=obras["estado"].map(ORDEN)).sort_values(["orden", "obra_codigo"])

    for obra in obras.itertuples():
        exceso = obra.sobrecosto_proyectado / obra.presupuesto if obra.presupuesto > 0 else 0
        lineas.append(f"{obra.estado[:1]} *{obra.obra_codigo}* {obra.obra}")
        lineas.append(f"   Avance {obra.avance:.0%} · gastado {millones(obra.gastado)} "
                      f"de {millones(obra.presupuesto)}")
        if obra.estado != calculos.EN_PRESUPUESTO:
            lineas.append(f"   Proyecta {millones(obra.proyeccion)} ({exceso:+.0%} sobre el presupuesto)")
            # Las partidas que más empujan el sobrecosto de esta obra.
            de_la_obra = partidas[(partidas["obra_id"] == obra.obra_id)
                                  & (partidas["sobrecosto_proyectado"] > 0)]
            for p in de_la_obra.nlargest(max_partidas, "sobrecosto_proyectado").itertuples():
                lineas.append(f"   • {p.partida}: +{millones(p.sobrecosto_proyectado)}")
        lineas.append("")

    rojas = (obras["estado"] == calculos.SOBRECOSTO).sum()
    amarillas = (obras["estado"] == calculos.EN_RIESGO).sum()
    lineas.append(f"{rojas} en rojo, {amarillas} en riesgo, de {len(obras)} obras.")
    return "\n".join(lineas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Resumen de alertas de costos.")
    parser.add_argument("--actual", action="store_true", help="usar data/costos.db en vez del ejemplo")
    parser.add_argument("--tolerancia", type=float, default=10, help="tolerancia en %% (por defecto 10)")
    args = parser.parse_args()

    if args.actual:
        con = db.conectar()
    else:
        con = db.conectar(":memory:")
        limpios, _, _ = importar.validar(demo.generar())
        importar.cargar(con, limpios)

    tolerancia = args.tolerancia / 100
    partidas = calculos.metricas_partidas(db.consulta(con, "resumen_partidas"), tolerancia)
    obras = calculos.resumen_obras(partidas, tolerancia)
    hoy = datetime.now(ZoneInfo("America/Costa_Rica")).strftime("%d/%m/%Y")
    print(resumen(partidas, obras, hoy))


if __name__ == "__main__":
    main()
