"""Práctica de pandas sobre la base del proyecto.

Completá cada función (cambiá el "return None") y revisá con:

    python practica/revisar_pandas.py

Cada función recibe tres DataFrames:
    obras     id, codigo, nombre, cliente, fecha_inicio, fecha_fin_prevista
    partidas  id, obra_id, nombre, categoria, presupuesto, avance (0 a 1)
    gastos    id, partida_id, fecha, proveedor, documento, descripcion, monto

Los nombres de las columnas del resultado tienen que ser los del enunciado.
Son las mismas preguntas de la práctica de SQL: si ya las resolviste ahí,
aquí se trata de traducirlas. Las instrucciones están en practica/README.md.
"""

import numpy as np
import pandas as pd


def ej1(obras, partidas, gastos):
    """Gastos mayores a 5 000 000. Columnas: fecha, proveedor, monto. De mayor a menor monto."""
    return None


def ej2(obras, partidas, gastos):
    """El total gastado entre todas las obras (un número)."""
    return None


def ej3(obras, partidas, gastos):
    """Los 5 gastos más grandes. Columnas: fecha, proveedor, monto. De mayor a menor."""
    return None


def ej4(obras, partidas, gastos):
    """Total pagado a cada proveedor. Columnas: proveedor, total. De mayor a menor total."""
    return None


def ej5(obras, partidas, gastos):
    """Proveedores con más de 20 gastos. Columnas: proveedor, n, total. De mayor a menor n."""
    return None


def ej6(obras, partidas, gastos):
    """Total gastado por obra. Columnas: codigo, total. Ordenado por codigo."""
    return None


def ej7(obras, partidas, gastos):
    """Partidas sin ningún gasto. Columnas: codigo, partida. Ordenado por codigo y partida."""
    return None


def ej8(obras, partidas, gastos):
    """Cuántos gastos hay de cada tamaño: 'Pequeño' (< 500 000), 'Mediano' (< 3 000 000), 'Grande'.
    Columnas: tamano, n. De mayor a menor n."""
    return None


def ej9(obras, partidas, gastos):
    """Gasto por mes de la obra OB-02. Columnas: mes (texto 'AAAA-MM'), gasto_mes. Ordenado por mes."""
    return None


def ej10(obras, partidas, gastos):
    """Igual que el 9, más dos columnas: gasto_acumulado y diferencia contra el mes anterior.
    Columnas: mes, gasto_mes, gasto_acumulado, diferencia. Ordenado por mes."""
    return None


def ej11(obras, partidas, gastos):
    """Tabla dinámica: una fila por obra (codigo) y una columna por categoria, con el presupuesto
    sumado. Donde una obra no tenga esa categoría va 0. Ordenado por codigo."""
    return None


def ej12(obras, partidas, gastos):
    """Reto. Por obra: codigo, presupuesto, gastado, pct_gastado (0 a 100, redondeado a 1 decimal).
    Ordenado por codigo. Ojo: el presupuesto de OB-01 tiene que dar 78 000 000."""
    return None
