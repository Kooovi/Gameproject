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


def _texto_o_nada(valor):
    """Texto sin espacios sobrantes, o None si la celda quedó vacía."""
    if valor is None or (isinstance(valor, float) and valor != valor):    # NaN != NaN
        return None
    return str(valor).strip() or None


def guardar_cambios_gastos(con: sqlite3.Connection, editados: list[dict], borrar: list[int]) -> None:
    """Aplica correcciones y borrados de gastos, todo junto.

    editados: una lista de dicts con gasto_id, fecha (date), proveedor, documento,
              descripcion y monto (los valores nuevos).
    borrar:   ids de los gastos a eliminar.

    Primero se valida todo; si una sola fila está mal no se cambia nada.
    """
    def vacio(valor):
        # Una celda borrada en la tabla puede llegar como None, NaN o NaT.
        # NaN y NaT tienen la rareza de no ser iguales a sí mismos.
        return valor is None or valor != valor

    for fila in editados:
        if vacio(fila["fecha"]):
            raise ValueError(f"El gasto {fila['gasto_id']} quedó sin fecha.")
        if vacio(fila["monto"]) or fila["monto"] <= 0:
            raise ValueError(f"El gasto {fila['gasto_id']} tiene que tener un monto mayor que cero.")

    with con:
        con.executemany(
            "UPDATE gastos SET fecha = ?, proveedor = ?, documento = ?, descripcion = ?, monto = ? "
            "WHERE id = ?",
            [(f["fecha"].isoformat(), _texto_o_nada(f["proveedor"]), _texto_o_nada(f["documento"]),
              _texto_o_nada(f["descripcion"]), float(f["monto"]), int(f["gasto_id"])) for f in editados],
        )
        con.executemany("DELETE FROM gastos WHERE id = ?", [(int(i),) for i in borrar])
