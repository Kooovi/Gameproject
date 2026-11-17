"""SOLUCIONES de la práctica de pandas. Intentá cada ejercicio antes de mirar aquí.

Cada función recibe las tres tablas como DataFrames y devuelve la respuesta.
Al lado de cada solución está el SQL equivalente, para ver la traducción.
"""

import numpy as np
import pandas as pd


def ej1(obras, partidas, gastos):
    """Gastos mayores a 5 000 000. Columnas: fecha, proveedor, monto. De mayor a menor monto."""
    # SQL: SELECT fecha, proveedor, monto FROM gastos WHERE monto > 5000000 ORDER BY monto DESC
    # gastos["monto"] > 5000000 da una columna de True/False; al ponerla entre
    # corchetes, pandas se queda solo con las filas donde es True.
    grandes = gastos[gastos["monto"] > 5_000_000]
    return grandes[["fecha", "proveedor", "monto"]].sort_values("monto", ascending=False)


def ej2(obras, partidas, gastos):
    """El total gastado entre todas las obras (un número)."""
    # SQL: SELECT SUM(monto) FROM gastos
    return gastos["monto"].sum()


def ej3(obras, partidas, gastos):
    """Los 5 gastos más grandes. Columnas: fecha, proveedor, monto. De mayor a menor."""
    # SQL: ... ORDER BY monto DESC LIMIT 5
    return gastos.nlargest(5, "monto")[["fecha", "proveedor", "monto"]]


def ej4(obras, partidas, gastos):
    """Total pagado a cada proveedor. Columnas: proveedor, total. De mayor a menor total."""
    # SQL: SELECT proveedor, SUM(monto) AS total FROM gastos GROUP BY proveedor ORDER BY total DESC
    # as_index=False deja "proveedor" como columna normal y no como índice.
    por_proveedor = gastos.groupby("proveedor", as_index=False).agg(total=("monto", "sum"))
    return por_proveedor.sort_values("total", ascending=False)


def ej5(obras, partidas, gastos):
    """Proveedores con más de 20 gastos. Columnas: proveedor, n, total. De mayor a menor n."""
    # SQL: ... GROUP BY proveedor HAVING COUNT(*) > 20 ORDER BY n DESC
    # En pandas no existe HAVING: se agrupa y después se filtra el resultado.
    por_proveedor = gastos.groupby("proveedor", as_index=False).agg(
        n=("monto", "count"),
        total=("monto", "sum"),
    )
    return por_proveedor[por_proveedor["n"] > 20].sort_values("n", ascending=False)


def _gastos_con_obra(obras, partidas, gastos):
    """Pega a cada gasto su partida y su obra (lo usan varios ejercicios)."""
    # merge es el JOIN de pandas. Como "id" y "nombre" existen en varias tablas,
    # primero se renombran para que no choquen.
    p = partidas.rename(columns={"id": "partida_id", "nombre": "partida"})
    o = obras.rename(columns={"id": "obra_id", "nombre": "obra"})
    return gastos.merge(p, on="partida_id").merge(o, on="obra_id")


def ej6(obras, partidas, gastos):
    """Total gastado por obra. Columnas: codigo, total. Ordenado por codigo."""
    # SQL: gastos JOIN partidas JOIN obras ... GROUP BY o.codigo
    todo = _gastos_con_obra(obras, partidas, gastos)
    return todo.groupby("codigo", as_index=False).agg(total=("monto", "sum")).sort_values("codigo")


def ej7(obras, partidas, gastos):
    """Partidas sin ningún gasto. Columnas: codigo, partida. Ordenado por codigo y partida."""
    # SQL: LEFT JOIN gastos ... WHERE g.id IS NULL
    # Otra forma de pensarlo: las partidas cuyo id NO aparece en gastos.
    # isin() pregunta "¿está en esta lista?" y ~ es la negación.
    sin_gasto = partidas[~partidas["id"].isin(gastos["partida_id"])]
    sin_gasto = sin_gasto.rename(columns={"nombre": "partida"})
    resultado = sin_gasto.merge(obras, left_on="obra_id", right_on="id")
    return resultado[["codigo", "partida"]].sort_values(["codigo", "partida"])


def ej8(obras, partidas, gastos):
    """Cuántos gastos hay de cada tamaño: 'Pequeño' (< 500 000), 'Mediano' (< 3 000 000), 'Grande'.
    Columnas: tamano, n. De mayor a menor n."""
    # SQL: CASE WHEN monto < 500000 THEN 'Pequeño' WHEN monto < 3000000 THEN 'Mediano' ELSE 'Grande' END
    # np.select es el CASE: una lista de condiciones, una de resultados y un valor por defecto.
    tamano = np.select(
        [gastos["monto"] < 500_000, gastos["monto"] < 3_000_000],
        ["Pequeño", "Mediano"],
        default="Grande",
    )
    conteo = gastos.assign(tamano=tamano).groupby("tamano", as_index=False).agg(n=("monto", "count"))
    return conteo.sort_values("n", ascending=False)


def ej9(obras, partidas, gastos):
    """Gasto por mes de la obra OB-02. Columnas: mes (texto 'AAAA-MM'), gasto_mes. Ordenado por mes."""
    # SQL: strftime('%Y-%m', fecha) ... GROUP BY mes
    # .dt da acceso a las funciones de fecha de una columna.
    todo = _gastos_con_obra(obras, partidas, gastos)
    ob2 = todo[todo["codigo"] == "OB-02"]
    ob2 = ob2.assign(mes=ob2["fecha"].dt.strftime("%Y-%m"))
    return ob2.groupby("mes", as_index=False).agg(gasto_mes=("monto", "sum")).sort_values("mes")


def ej10(obras, partidas, gastos):
    """Igual que el 9, más dos columnas: gasto_acumulado y diferencia contra el mes anterior.
    Columnas: mes, gasto_mes, gasto_acumulado, diferencia. Ordenado por mes."""
    # SQL: SUM(gasto_mes) OVER (ORDER BY mes)  y  gasto_mes - LAG(gasto_mes) OVER (ORDER BY mes)
    mensual = ej9(obras, partidas, gastos)
    return mensual.assign(
        gasto_acumulado=mensual["gasto_mes"].cumsum(),   # suma corrida
        diferencia=mensual["gasto_mes"].diff(),          # fila actual menos la anterior
    )


def ej11(obras, partidas, gastos):
    """Tabla dinámica: una fila por obra (codigo) y una columna por categoria, con el presupuesto
    sumado. Donde una obra no tenga esa categoría va 0. Ordenado por codigo."""
    # Es exactamente una tabla dinámica de Excel: filas, columnas, valores y función.
    con_obra = partidas.merge(obras, left_on="obra_id", right_on="id")
    return con_obra.pivot_table(
        index="codigo", columns="categoria", values="presupuesto", aggfunc="sum", fill_value=0,
    )


def ej12(obras, partidas, gastos):
    """Reto. Por obra: codigo, presupuesto, gastado, pct_gastado (0 a 100, redondeado a 1 decimal).
    Ordenado por codigo. Ojo: el presupuesto de OB-01 tiene que dar 78 000 000."""
    # LA TRAMPA es la misma que en SQL: si se pegan los gastos a las partidas y después
    # se suma el presupuesto, cada partida se cuenta una vez por cada gasto.
    # Se suma cada cosa por separado y al final se unen los totales.
    presupuesto = partidas.groupby("obra_id", as_index=False).agg(presupuesto=("presupuesto", "sum"))
    gastado = (
        gastos.merge(partidas, left_on="partida_id", right_on="id")
        .groupby("obra_id", as_index=False)
        .agg(gastado=("monto", "sum"))
    )
    resumen = obras.merge(presupuesto, left_on="id", right_on="obra_id").merge(gastado, on="obra_id")
    resumen["pct_gastado"] = (100 * resumen["gastado"] / resumen["presupuesto"]).round(1)
    return resumen[["codigo", "presupuesto", "gastado", "pct_gastado"]].sort_values("codigo")
