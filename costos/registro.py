"""Cambios del día a día sin pasar por Excel: registrar un gasto y actualizar avances.

Cada función valida antes de escribir y usa "with con:" para que el cambio
quede guardado completo o no quede del todo.
"""

import sqlite3
from datetime import date


def agregar_gasto(con: sqlite3.Connection, partida_id: int, fecha: date, monto: float,
                  proveedor: str = "", documento: str = "", descripcion: str = "") -> int:
    """Inserta un gasto y devuelve su id. Lanza ValueError si el monto no sirve."""
    if not monto or monto <= 0:
        raise ValueError("El monto debe ser mayor que cero.")
    with con:
        cur = con.execute(
            "INSERT INTO gastos (partida_id, fecha, proveedor, documento, descripcion, monto) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            # "or None": un texto vacío se guarda como NULL, no como "".
            (partida_id, fecha.isoformat(), proveedor.strip() or None,
             documento.strip() or None, descripcion.strip() or None, float(monto)),
        )
    return cur.lastrowid


def actualizar_avances(con: sqlite3.Connection, avances: dict[int, float]) -> None:
    """Recibe {partida_id: avance} con el avance entre 0 y 1."""
    for avance in avances.values():
        if not 0 <= avance <= 1:
            raise ValueError("El avance debe estar entre 0 % y 100 %.")
    with con:
        # executemany corre el mismo UPDATE una vez por cada par (avance, id).
        con.executemany("UPDATE partidas SET avance = ? WHERE id = ?",
                        [(avance, partida_id) for partida_id, avance in avances.items()])
