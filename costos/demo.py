"""Datos de ejemplo. TODO ES FICTICIO: obras, clientes, proveedores y montos.

Sirven para probar la herramienta y para la plantilla de Excel. Se generan con
una semilla fija, así que siempre salen los mismos números (reproducible).

Devuelve los datos en el mismo formato que el Excel (tres tablas), para que
pasen por el mismo camino de validar() y cargar() que los datos reales.
"""

import random
from datetime import date, timedelta

import pandas as pd

HOY = date(2026, 10, 31)  # fecha de corte fija para que el ejemplo no cambie con el tiempo

# (partida, categoría, proporción del presupuesto total de la obra)
PARTIDAS = [
    ("Obras preliminares", "Mano de obra", 0.04),
    ("Cimientos", "Materiales", 0.14),
    ("Estructura y paredes", "Materiales", 0.26),
    ("Techos", "Materiales", 0.12),
    ("Instalación eléctrica", "Subcontratos", 0.10),
    ("Instalación mecánica", "Subcontratos", 0.08),
    ("Acabados", "Materiales", 0.20),
    ("Gastos indirectos", "Indirectos", 0.06),
]

PROVEEDORES = {
    "Materiales": ["Depósito El Roble", "Ferretería La Cumbre", "Concretos del Valle", "Aceros Tibás"],
    "Mano de obra": ["Planilla quincenal"],
    "Subcontratos": ["Electromecánica Irazú", "Instalaciones Poás"],
    "Indirectos": ["Alquiler de equipo Turrialba", "Transportes Barva", "Caja chica"],
}

# Cada obra cuenta una historia distinta. "ritmo" es cuánto se gasta por cada
# colón de avance: 1.0 = justo lo presupuestado, 1.2 = 20 % más caro.
OBRAS = [
    # código, nombre, cliente, inicio, fin, presupuesto total, avances por partida, ritmo general
    ("OB-01", "Casa de habitación Los Cipreses", "Familia Rojas (ficticia)",
     date(2026, 3, 2), date(2026, 12, 18), 78_000_000,
     [100, 100, 100, 90, 70, 60, 35, 75], 0.97),
    ("OB-02", "Bodega industrial El Coyol", "Logística Tica S.A. (ficticia)",
     date(2026, 5, 11), date(2027, 2, 26), 215_000_000,
     [100, 100, 65, 20, 15, 10, 0, 50], 1.06),
    ("OB-03", "Remodelación local comercial Escazú", "Café Aurora (ficticio)",
     date(2026, 6, 15), date(2026, 11, 27), 42_000_000,
     [100, 100, 100, 100, 85, 80, 60, 85], 1.19),
    ("OB-04", "Apartamentos Vista Verde", "Inversiones Zurquí (ficticia)",
     date(2026, 9, 7), date(2027, 8, 20), 340_000_000,
     [80, 25, 0, 0, 0, 0, 0, 10], 1.00),
]


def generar(semilla: int = 7) -> dict[str, pd.DataFrame]:
    rng = random.Random(semilla)
    obras, presupuesto, gastos = [], [], []

    for codigo, nombre, cliente, inicio, fin, total, avances, ritmo in OBRAS:
        obras.append({"codigo": codigo, "nombre": nombre, "cliente": cliente,
                      "fecha_inicio": inicio, "fecha_fin_prevista": fin})
        dias = (HOY - inicio).days

        for i, ((partida, categoria, peso), avance) in enumerate(zip(PARTIDAS, avances)):
            monto_partida = round(total * peso, -3)  # redondeado a miles
            presupuesto.append({"obra": codigo, "partida": partida, "categoria": categoria,
                                "presupuesto": monto_partida, "avance_pct": avance})
            if avance == 0:
                continue

            # Lo gastado = presupuesto x avance x ritmo, con algo de ruido por partida.
            gastado = monto_partida * avance / 100 * ritmo * rng.uniform(0.93, 1.07)

            # Se reparte en varias facturas, en la ventana de tiempo de esa partida.
            n = rng.randint(4, 9)
            cortes = sorted(rng.random() for _ in range(n - 1))
            partes = [b - a for a, b in zip([0, *cortes], [*cortes, 1])]
            desde = dias * i / len(PARTIDAS) * 0.8
            for parte in partes:
                dia = int(rng.uniform(desde, dias)) if categoria != "Indirectos" else rng.randint(0, dias)
                gastos.append({
                    "fecha": inicio + timedelta(days=dia),
                    "obra": codigo,
                    "partida": partida,
                    "proveedor": rng.choice(PROVEEDORES[categoria]),
                    "documento": f"F-{rng.randint(10000, 99999)}",
                    "descripcion": f"{partida} - pago parcial",
                    "monto": round(gastado * parte, -2),
                })

    # Un gasto que nadie presupuestó, para mostrar cómo lo destapa la herramienta.
    gastos.append({"fecha": date(2026, 9, 22), "obra": "OB-03", "partida": "Reparación de fuga",
                   "proveedor": "Instalaciones Poás", "documento": "F-55012",
                   "descripcion": "Fuga en tubería existente del local", "monto": 1_350_000})

    tabla_gastos = pd.DataFrame(gastos).sort_values(["fecha", "obra"]).reset_index(drop=True)
    return {"Obras": pd.DataFrame(obras), "Presupuesto": pd.DataFrame(presupuesto), "Gastos": tabla_gastos}
