"""Salidas a Excel: el respaldo de todos los datos y el reporte de una obra."""

import io
import sqlite3

import pandas as pd

from costos import importar


def datos_completos(con: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    """Saca todo de la base en el mismo formato de la plantilla (tres hojas).

    Lo que sale de aquí se puede volver a subir en "Cargar datos": sirve de respaldo.
    """
    obras = pd.read_sql_query(
        "SELECT codigo, nombre, cliente, fecha_inicio, fecha_fin_prevista FROM obras ORDER BY codigo", con)
    presupuesto = pd.read_sql_query(
        "SELECT o.codigo AS obra, p.nombre AS partida, p.categoria, p.presupuesto, "
        "       p.avance * 100 AS avance_pct "
        "FROM partidas p JOIN obras o ON o.id = p.obra_id ORDER BY o.codigo, p.id", con)
    gastos = pd.read_sql_query(
        "SELECT g.fecha, o.codigo AS obra, p.nombre AS partida, g.proveedor, g.documento, "
        "       g.descripcion, g.monto "
        "FROM gastos g JOIN partidas p ON p.id = g.partida_id JOIN obras o ON o.id = p.obra_id "
        "ORDER BY g.fecha, g.id", con)
    return {"Obras": obras, "Presupuesto": presupuesto, "Gastos": gastos}


def respaldo_excel(con: sqlite3.Connection) -> bytes:
    archivo = io.BytesIO()          # un "archivo" en memoria, sin tocar el disco
    importar.escribir_excel(datos_completos(con), archivo)
    return archivo.getvalue()


def reporte_obra_excel(obra: pd.Series, partidas: pd.DataFrame, gastos: pd.DataFrame) -> bytes:
    """Reporte de una obra con tres hojas: Resumen, Partidas y Gastos."""
    resumen = pd.DataFrame({
        "Indicador": ["Obra", "Estado", "Presupuesto", "Gastado", "Avance", "% gastado",
                      "Desviación", "Proyección final", "Sobrecosto proyectado"],
        "Valor": [f"{obra['obra_codigo']} · {obra['obra']}", obra["estado"], obra["presupuesto"],
                  obra["gastado"], obra["avance"], obra["pct_gastado"], obra["desviacion"],
                  obra["proyeccion"], obra["sobrecosto_proyectado"]],
    })
    columnas = {
        "partida": "Partida", "categoria": "Categoría", "estado": "Estado",
        "presupuesto": "Presupuesto", "gastado": "Gastado", "disponible": "Disponible",
        "avance": "Avance", "pct_gastado": "% gastado", "desviacion": "Desviación",
        "proyeccion": "Proyección final", "sobrecosto_proyectado": "Sobrecosto proyectado",
    }
    hojas = {
        "Resumen": resumen,
        "Partidas": partidas[list(columnas)].rename(columns=columnas),
        "Gastos": gastos,
    }

    archivo = io.BytesIO()
    with pd.ExcelWriter(archivo, engine="openpyxl") as writer:
        for nombre, df in hojas.items():
            df.to_excel(writer, sheet_name=nombre, index=False)
            hoja = writer.sheets[nombre]
            for i, columna in enumerate(df.columns):
                letra = chr(65 + i)
                hoja.column_dimensions[letra].width = 24 if i == 0 else 20
                # Formato de celda de Excel: porcentaje o número con separador de miles.
                if columna in ("Avance", "% gastado"):
                    formato = "0%"
                elif pd.api.types.is_numeric_dtype(df[columna]):
                    formato = "#,##0"
                else:
                    continue
                for celda in hoja[letra][1:]:      # [1:] se salta el encabezado
                    celda.number_format = formato
    return archivo.getvalue()
