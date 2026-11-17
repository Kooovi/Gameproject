"""Cálculos de control de costos, hechos con pandas.

SQL hace el trabajo de juntar y sumar (ver sql/resumen_partidas.sql).
Aquí se calculan los indicadores a partir de esas sumas.

Idea central: comparar gasto contra presupuesto NO basta. Si una partida lleva
gastado el 60 % del presupuesto pero solo va por el 40 % de avance, va mal
aunque todavía "quede plata". Por eso todo se compara contra el avance.
"""

import pandas as pd

EN_PRESUPUESTO = "🟢 En presupuesto"
EN_RIESGO = "🟡 En riesgo"
SOBRECOSTO = "🔴 Sobrecosto"


def _estado(proyeccion: float, presupuesto: float, tolerancia: float) -> str:
    """Semáforo según cuánto se pasa la proyección final del presupuesto."""
    if proyeccion <= presupuesto:
        return EN_PRESUPUESTO
    if proyeccion <= presupuesto * (1 + tolerancia):
        return EN_RIESGO
    return SOBRECOSTO


def metricas_partidas(df: pd.DataFrame, tolerancia: float = 0.10) -> pd.DataFrame:
    """Agrega los indicadores a la tabla de partidas.

    Espera las columnas: presupuesto, avance (0 a 1) y gastado.
    """
    df = df.copy()

    # Cuánta plata queda de lo presupuestado (negativo = ya se pasó).
    df["disponible"] = df["presupuesto"] - df["gastado"]

    # Qué fracción del presupuesto se ha gastado. Si el presupuesto es 0
    # (gasto sin presupuestar) no se puede dividir: queda vacío.
    df["pct_gastado"] = (df["gastado"] / df["presupuesto"]).where(df["presupuesto"] > 0)

    # Lo que "debería" llevar gastado según el avance físico.
    df["costo_esperado"] = df["presupuesto"] * df["avance"]

    # Positivo = se ha gastado más de lo que el avance justifica.
    df["desviacion"] = df["gastado"] - df["costo_esperado"]

    # Proyección del costo final: si con X % de avance se gastó G,
    # al mismo ritmo el 100 % costará G / X.
    # Sin avance no hay ritmo que medir: se asume el presupuesto
    # (o lo ya gastado, si ya lo superó).
    al_ritmo_actual = df["gastado"] / df["avance"].where(df["avance"] > 0)
    sin_avance = df[["presupuesto", "gastado"]].max(axis=1)
    df["proyeccion"] = al_ritmo_actual.fillna(sin_avance)

    df["sobrecosto_proyectado"] = df["proyeccion"] - df["presupuesto"]

    df["estado"] = [
        _estado(proy, pres, tolerancia)
        for proy, pres in zip(df["proyeccion"], df["presupuesto"])
    ]
    return df


def resumen_obras(partidas: pd.DataFrame, tolerancia: float = 0.10) -> pd.DataFrame:
    """Una fila por obra, sumando sus partidas (que ya traen las métricas)."""
    obras = partidas.groupby(["obra_id", "obra_codigo", "obra"], as_index=False).agg(
        presupuesto=("presupuesto", "sum"),
        gastado=("gastado", "sum"),
        costo_esperado=("costo_esperado", "sum"),
        proyeccion=("proyeccion", "sum"),
        partidas_en_rojo=("estado", lambda s: int((s == SOBRECOSTO).sum())),
    )
    con_presupuesto = obras["presupuesto"] > 0
    # Avance de la obra = promedio de los avances ponderado por presupuesto:
    # una partida de 50 millones pesa más que una de 2.
    obras["avance"] = (obras["costo_esperado"] / obras["presupuesto"]).where(con_presupuesto, 0)
    obras["pct_gastado"] = (obras["gastado"] / obras["presupuesto"]).where(con_presupuesto)
    obras["disponible"] = obras["presupuesto"] - obras["gastado"]
    obras["desviacion"] = obras["gastado"] - obras["costo_esperado"]
    obras["sobrecosto_proyectado"] = obras["proyeccion"] - obras["presupuesto"]
    obras["estado"] = [
        _estado(proy, pres, tolerancia)
        for proy, pres in zip(obras["proyeccion"], obras["presupuesto"])
    ]
    return obras
