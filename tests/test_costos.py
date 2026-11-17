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


# ---------------------------------------------------------------- registrar y exportar

def _base_minima():
    con = db.conectar(":memory:")
    limpios, _, _ = importar.validar(_datos_minimos())
    importar.cargar(con, limpios)
    partida_id = int(db.consulta(con, "resumen_partidas").iloc[0]["partida_id"])
    return con, partida_id


def test_agregar_gasto_suma_al_gastado():
    from datetime import date
    from costos import registro
    con, partida_id = _base_minima()
    registro.agregar_gasto(con, partida_id, date(2026, 4, 1), 100, proveedor="  Ferretería  ")
    assert db.consulta(con, "resumen_partidas").iloc[0]["gastado"] == 500       # 400 + 100
    assert con.execute("SELECT proveedor FROM gastos ORDER BY id DESC").fetchone()[0] == "Ferretería"

    with pytest.raises(ValueError):
        registro.agregar_gasto(con, partida_id, date(2026, 4, 1), 0)


def test_actualizar_avances():
    from costos import registro
    con, partida_id = _base_minima()
    registro.actualizar_avances(con, {partida_id: 0.8})
    assert db.consulta(con, "resumen_partidas").iloc[0]["avance"] == 0.8

    with pytest.raises(ValueError):
        registro.actualizar_avances(con, {partida_id: 1.5})


def test_el_respaldo_se_puede_volver_a_cargar():
    from costos import exportar
    con = db.conectar(":memory:")
    limpios, _, _ = importar.validar(demo.generar())
    importar.cargar(con, limpios)
    antes = db.consulta(con, "resumen_partidas")

    respaldo = io.BytesIO(exportar.respaldo_excel(con))
    limpios, errores, avisos = importar.validar(importar.leer_excel(respaldo))
    assert errores == [] and avisos == []      # la partida sin presupuestar ya viene en el respaldo
    otra = db.conectar(":memory:")
    importar.cargar(otra, limpios)
    # Se compara todo menos los id internos, que la base vuelve a numerar al cargar.
    columnas = ["obra_codigo", "partida", "presupuesto", "avance", "gastado", "n_gastos"]
    orden = ["obra_codigo", "partida"]
    despues = db.consulta(otra, "resumen_partidas")
    pd.testing.assert_frame_equal(
        antes[columnas].sort_values(orden).reset_index(drop=True),
        despues[columnas].sort_values(orden).reset_index(drop=True),
    )
    assert db.consulta(con, "gasto_mensual").equals(db.consulta(otra, "gasto_mensual"))   # mismas fechas


def test_reporte_de_obra_tiene_tres_hojas():
    from costos import exportar
    con = db.conectar(":memory:")
    limpios, _, _ = importar.validar(demo.generar())
    importar.cargar(con, limpios)
    partidas = calculos.metricas_partidas(db.consulta(con, "resumen_partidas"))
    obra = calculos.resumen_obras(partidas).iloc[0]
    de_la_obra = partidas[partidas["obra_id"] == obra["obra_id"]]
    archivo = exportar.reporte_obra_excel(obra, de_la_obra, db.consulta(con, "gastos_detalle", (int(obra["obra_id"]),)))
    hojas = pd.read_excel(io.BytesIO(archivo), sheet_name=None)
    assert list(hojas) == ["Resumen", "Partidas", "Gastos"]
    assert hojas["Partidas"]["Gastado"].sum() == pytest.approx(obra["gastado"])


def test_fechas_en_texto_se_leen_dia_primero():
    fechas = importar._fechas(pd.Series(["03/04/2026", "2026-04-03", "3-4-2026", "no es fecha", None]))
    assert list(fechas.dt.strftime("%Y-%m-%d"))[:3] == ["2026-04-03"] * 3
    assert fechas.isna().tolist() == [False, False, False, True, True]


# ---------------------------------------------------------------- práctica de SQL

def test_las_soluciones_de_la_practica_corren_y_devuelven_filas():
    import sys
    sys.path.insert(0, str(db.RAIZ / "practica"))
    import revisar

    soluciones = revisar.leer_ejercicios(db.RAIZ / "practica" / "soluciones.sql")
    enunciados = revisar.leer_ejercicios(db.RAIZ / "practica" / "ejercicios.sql")
    assert sorted(soluciones) == sorted(enunciados) == list(range(1, 21))

    con = db.conectar(":memory:")
    limpios, _, _ = importar.validar(demo.generar())
    importar.cargar(con, limpios)
    for numero, solucion in soluciones.items():
        assert con.execute(solucion["sql"]).fetchall(), f"la solución {numero} no devuelve filas"


def test_las_soluciones_de_pandas_pasan_su_propio_revisor():
    import sys
    sys.path.insert(0, str(db.RAIZ / "practica"))
    import pandas_ejercicios
    import pandas_soluciones
    import revisar_pandas

    tablas = revisar_pandas.cargar_tablas()
    for numero in range(1, revisar_pandas.TOTAL + 1):
        esperado = getattr(pandas_soluciones, f"ej{numero}")(*(t.copy() for t in tablas))
        assert revisar_pandas.comparar(esperado, esperado) is None
        # Los ejercicios se entregan sin resolver.
        assert getattr(pandas_ejercicios, f"ej{numero}")(*tablas) is None
    # El reto no cae en la trampa de duplicar el presupuesto.
    reto = pandas_soluciones.ej12(*tablas).set_index("codigo")
    assert reto.loc["OB-01", "presupuesto"] == 78_000_000


# ---------------------------------------------------------------- Excel "sucio"

@pytest.mark.parametrize("celda, esperado", [
    (1250000, 1250000), (1250000.5, 1250000.5),
    ("₡1.250.000,50", 1250000.5),      # formato de Costa Rica
    ("1,250,000.50", 1250000.5),       # formato de Estados Unidos
    ("₡ 1.250.000", 1250000), ("1,250,000", 1250000),
    ("1250,5", 1250.5), ("1250.5", 1250.5), ("-3.500", -3500), ("35%", 35),
    ("abc", None), ("", None), (None, None),
])
def test_lectura_de_montos(celda, esperado):
    assert importar._numero(celda) == esperado


def test_excel_sucio_se_carga_igual():
    datos = {
        "Obras": pd.DataFrame({" Código ": [1.0], "NOMBRE": ["Obra A"]}),          # código numérico
        "Presupuesto": pd.DataFrame({
            "Obra": [1, 1], "Partida": ["Cimientos", "Techos"],
            "Presupuesto": ["₡1.000.000,00", "₡500.000,00"], "Avance %": [0.5, 0.25],   # avance como fracción
        }),
        "Gastos": pd.DataFrame({
            "Fecha": ["15/03/2026", "16/03/2026"], "Obra": ["1", "1"],
            "Partida": ["cimientos ", "TECHOS"], "Descripción": ["Cemento", "Láminas"],
            "Monto": ["400.000", "₡100.000,50"],
        }),
    }
    limpios, errores, avisos = importar.validar(datos)
    assert errores == []
    assert len(avisos) == 1 and "fracción" in avisos[0]        # avisa del avance, no crea partidas de más

    con = db.conectar(":memory:")
    importar.cargar(con, limpios)
    partidas = db.consulta(con, "resumen_partidas").set_index("partida")
    assert list(partidas.index) == ["Cimientos", "Techos"]
    assert partidas.loc["Cimientos", ["presupuesto", "avance", "gastado"]].tolist() == [1_000_000, 0.5, 400_000]
    assert partidas.loc["Techos", ["presupuesto", "avance", "gastado"]].tolist() == [500_000, 0.25, 100_000.5]
    assert con.execute("SELECT descripcion FROM gastos ORDER BY id").fetchall() == [("Cemento",), ("Láminas",)]


def test_archivo_sin_gastos_y_obra_sin_partidas():
    datos = {
        "Obras": pd.DataFrame({"codigo": ["A", "B"], "nombre": ["Obra A", "Obra B"]}),
        "Presupuesto": pd.DataFrame({"obra": ["A"], "partida": ["Cimientos"], "presupuesto": [1000]}),
        "Gastos": pd.DataFrame(columns=["fecha", "obra", "partida", "monto"]),      # hoja vacía
    }
    limpios, errores, avisos = importar.validar(datos)
    assert errores == []
    assert len(avisos) == 1 and "Obra B" in avisos[0]

    con = db.conectar(":memory:")
    importar.cargar(con, limpios)
    partidas = calculos.metricas_partidas(db.consulta(con, "resumen_partidas"))
    obra = calculos.resumen_obras(partidas).iloc[0]
    assert (obra["gastado"], obra["proyeccion"], obra["estado"]) == (0, 1000, calculos.EN_PRESUPUESTO)
    assert db.consulta(con, "gasto_mensual").empty


def test_avance_vacio_no_se_guarda():
    from costos import registro
    con, partida_id = _base_minima()
    with pytest.raises(ValueError):
        registro.actualizar_avances(con, {partida_id: float("nan")})
    assert db.consulta(con, "resumen_partidas").iloc[0]["avance"] == 0.5        # quedó como estaba


# ---------------------------------------------------------------- exportación a Power BI

def test_exportacion_powerbi(tmp_path):
    from costos import powerbi
    con = db.conectar(":memory:")
    limpios, _, _ = importar.validar(demo.generar())
    importar.cargar(con, limpios)
    powerbi.exportar(con, tmp_path)

    gastos = pd.read_csv(tmp_path / "gastos.csv", encoding="utf-8-sig")
    calendario = pd.read_csv(tmp_path / "calendario.csv", encoding="utf-8-sig")
    verificacion = pd.read_csv(tmp_path / "verificacion.csv", encoding="utf-8-sig").set_index("obra_codigo")

    # Cada fecha de gasto existe en el calendario (si no, la relación en Power BI falla).
    assert gastos["fecha"].isin(calendario["fecha"]).all()
    assert calendario["fecha"].is_unique
    assert verificacion.loc["TOTAL", "gastado"] == pytest.approx(gastos["monto"].sum())
    assert verificacion.loc["OB-01", "presupuesto"] == 78_000_000


def test_corregir_y_borrar_gastos():
    from datetime import date
    from costos import registro
    con, partida_id = _base_minima()
    nuevo = registro.agregar_gasto(con, partida_id, date(2026, 4, 1), 100)
    original = int(con.execute("SELECT MIN(id) FROM gastos").fetchone()[0])

    registro.guardar_cambios_gastos(
        con,
        [{"gasto_id": original, "fecha": date(2026, 3, 20), "proveedor": " Nuevo ",
          "documento": None, "descripcion": float("nan"), "monto": 450}],
        borrar=[nuevo],
    )
    filas = con.execute("SELECT id, fecha, proveedor, descripcion, monto FROM gastos").fetchall()
    assert filas == [(original, "2026-03-20", "Nuevo", None, 450)]

    # Si una fila es inválida no se aplica nada, ni siquiera los borrados.
    with pytest.raises(ValueError):
        registro.guardar_cambios_gastos(
            con, [{"gasto_id": original, "fecha": None, "proveedor": "", "documento": "",
                   "descripcion": "", "monto": 450}], borrar=[original])
    assert con.execute("SELECT COUNT(*) FROM gastos").fetchone()[0] == 1

    # Celdas borradas en la tabla de la app llegan como NaT / NaN.
    for fecha, monto in ((pd.NaT, 450), (date(2026, 3, 20), float("nan"))):
        with pytest.raises(ValueError):
            registro.guardar_cambios_gastos(
                con, [{"gasto_id": original, "fecha": fecha, "proveedor": "", "documento": "",
                       "descripcion": "", "monto": monto}], borrar=[])


def test_hojas_obras_o_presupuesto_vacias_son_error():
    datos = _datos_minimos()
    datos["Presupuesto"] = datos["Presupuesto"].iloc[0:0]
    datos["Gastos"] = datos["Gastos"].iloc[0:0]
    _, errores, _ = importar.validar(datos)
    assert errores == ["Hoja Presupuesto: no tiene ninguna partida"]

    datos = _datos_minimos()
    datos["Obras"] = datos["Obras"].iloc[0:0]
    _, errores, _ = importar.validar(datos)
    assert "Hoja Obras: no tiene ninguna obra" in errores
