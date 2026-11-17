"""Pruebas automáticas. Se corren con:  pytest

Cada prueba arma un caso chiquito con números fáciles de calcular a mano
y revisa que el programa dé ese mismo resultado.
"""

import io

import pandas as pd
import pytest

from costos import calculos, db, demo, importar


def _partidas(**columnas):
    return pd.DataFrame(columnas)


# ---------------------------------------------------------------- cálculos

def test_metricas_de_una_partida_que_va_cara():
    # Presupuesto 100, va por el 40 % y ya gastó 60.
    r = calculos.metricas_partidas(_partidas(presupuesto=[100.0], avance=[0.4], gastado=[60.0])).iloc[0]
    assert r["disponible"] == 40
    assert r["pct_gastado"] == pytest.approx(0.60)
    assert r["costo_esperado"] == pytest.approx(40)       # debería llevar 40
    assert r["desviacion"] == pytest.approx(20)           # lleva 20 de más
    assert r["proyeccion"] == pytest.approx(150)          # 60 / 0.4
    assert r["estado"] == calculos.SOBRECOSTO


def test_semaforo_respeta_la_tolerancia():
    df = _partidas(presupuesto=[100.0, 100.0, 100.0], avance=[0.5, 0.5, 0.5], gastado=[50.0, 54.0, 60.0])
    estados = list(calculos.metricas_partidas(df, tolerancia=0.10)["estado"])
    # Proyecciones: 100 (justo), 108 (dentro del 10 %), 120 (fuera).
    assert estados == [calculos.EN_PRESUPUESTO, calculos.EN_RIESGO, calculos.SOBRECOSTO]


def test_partida_sin_avance_proyecta_el_presupuesto():
    df = _partidas(presupuesto=[100.0, 100.0], avance=[0.0, 0.0], gastado=[0.0, 130.0])
    r = calculos.metricas_partidas(df)
    assert list(r["proyeccion"]) == [100, 130]            # la segunda ya se pasó sin avanzar


def test_gasto_sin_presupuestar_sale_en_rojo():
    r = calculos.metricas_partidas(_partidas(presupuesto=[0.0], avance=[0.0], gastado=[500.0])).iloc[0]
    assert pd.isna(r["pct_gastado"])                      # no se divide entre cero
    assert r["estado"] == calculos.SOBRECOSTO


def test_resumen_por_obra_pondera_el_avance_por_presupuesto():
    df = _partidas(
        obra_id=[1, 1], obra_codigo=["A", "A"], obra=["Obra A", "Obra A"],
        presupuesto=[900.0, 100.0], avance=[1.0, 0.0], gastado=[900.0, 0.0],
    )
    obra = calculos.resumen_obras(calculos.metricas_partidas(df)).iloc[0]
    assert obra["presupuesto"] == 1000
    assert obra["avance"] == pytest.approx(0.90)          # no 0.50: la partida grande pesa más
    assert obra["estado"] == calculos.EN_PRESUPUESTO


# ---------------------------------------------------------------- importar

def _datos_minimos():
    return {
        "Obras": pd.DataFrame({"codigo": ["A"], "nombre": ["Obra A"]}),
        "Presupuesto": pd.DataFrame({"obra": ["A"], "partida": ["Cimientos"], "presupuesto": [1000], "avance_pct": [50]}),
        "Gastos": pd.DataFrame({"fecha": ["15/03/2026"], "obra": ["A"], "partida": ["Cimientos"], "monto": [400]}),
    }


def test_importar_y_consultar_de_punta_a_punta():
    limpios, errores, avisos = importar.validar(_datos_minimos())
    assert errores == [] and avisos == []

    con = db.conectar(":memory:")
    importar.cargar(con, limpios)
    fila = db.consulta(con, "resumen_partidas").iloc[0]
    assert (fila["presupuesto"], fila["avance"], fila["gastado"]) == (1000, 0.5, 400)
    # La fecha 15/03/2026 se leyó como día/mes/año.
    assert db.consulta(con, "gasto_mensual").iloc[0]["mes"] == "2026-03"


def test_los_errores_dicen_hoja_y_fila():
    datos = _datos_minimos()
    datos["Gastos"] = pd.DataFrame({
        "fecha": ["15/03/2026", "no es fecha"], "obra": ["A", "Z"],
        "partida": ["Cimientos", "Cimientos"], "monto": ["abc", 100],
    })
    _, errores, _ = importar.validar(datos)
    assert "Hoja Gastos, fila 2: el monto debe ser un número" in errores
    assert "Hoja Gastos, fila 3: la fecha está vacía o no es válida" in errores
    assert "Hoja Gastos, fila 3: la obra no existe en la hoja Obras" in errores


def test_gasto_en_partida_no_presupuestada_se_carga_con_aviso():
    datos = _datos_minimos()
    datos["Gastos"].loc[0, "partida"] = "Imprevisto"
    limpios, errores, avisos = importar.validar(datos)
    assert errores == []
    assert len(avisos) == 1 and "Imprevisto" in avisos[0]

    con = db.conectar(":memory:")
    importar.cargar(con, limpios)
    partidas = db.consulta(con, "resumen_partidas").set_index("partida")
    assert partidas.loc["Imprevisto", "presupuesto"] == 0
    assert partidas.loc["Imprevisto", "gastado"] == 400


def test_falta_una_columna_obligatoria():
    datos = _datos_minimos()
    datos["Gastos"] = datos["Gastos"].drop(columns="monto")
    _, errores, _ = importar.validar(datos)
    assert errores == ["Hoja Gastos: faltan las columnas monto"]


def test_los_datos_demo_pasan_por_excel_sin_errores():
    # Escribe la plantilla a un Excel en memoria, lo vuelve a leer y lo carga.
    archivo = io.BytesIO()
    importar.escribir_excel(demo.generar(), archivo)
    archivo.seek(0)
    limpios, errores, avisos = importar.validar(importar.leer_excel(archivo))
    assert errores == []
    assert len(avisos) == 1                               # la "Reparación de fuga" de OB-03

    con = db.conectar(":memory:")
    importar.cargar(con, limpios)
    obras = calculos.resumen_obras(calculos.metricas_partidas(db.consulta(con, "resumen_partidas")))
    assert len(obras) == 4
    # Lo que suma SQL coincide con sumar la hoja de gastos directamente.
    assert obras["gastado"].sum() == pytest.approx(limpios["Gastos"]["monto"].sum())
