"""Interfaz web (Streamlit). Se corre con:  streamlit run streamlit_app.py

Este archivo solo dibuja la pantalla. La lógica vive en el paquete costos/:
  - costos/db.py        consultas SQL -> DataFrames
  - costos/calculos.py  indicadores con pandas
  - costos/importar.py  Excel -> validación -> base de datos
  - costos/registro.py  registrar un gasto / actualizar avances
  - costos/exportar.py  respaldo y reporte en Excel
"""

import io
from datetime import datetime
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

from costos import calculos, db, demo, exportar, importar, registro

AZUL = "#2a78d6"   # lo gastado
GRIS = "#6f6e69"   # la referencia (presupuesto)

st.set_page_config(page_title="Control de costos por obra", page_icon="🏗️", layout="wide")


# ------------------------------------------------------------------ utilidades

def colones(x) -> str:
    """Formato de moneda. El signo va antes del símbolo: -₡1,500."""
    if pd.isna(x):
        return "—"
    return f"{'-' if x < 0 else ''}₡{abs(x):,.0f}"


def diferencia(x) -> str | None:
    """Igual que colones() pero con + explícito, para que st.metric sepa si subió o bajó.

    Si la diferencia es menos de ₡1 devuelve None: st.metric no muestra flecha.
    """
    if abs(x) < 1:
        return None
    return f"{'+' if x > 0 else ''}{colones(x)} vs. presupuesto"


def pct(x) -> str:
    return "—" if pd.isna(x) else f"{x:.0%}"


FORMATO = {
    "Presupuesto": colones, "Gastado": colones, "Disponible": colones,
    "Desviación": colones, "Proyección final": colones, "Sobrecosto proyectado": colones,
    "Total": colones, "Monto": colones, "Avance": pct, "% gastado": pct,
}

NOMBRES = {
    "obra_codigo": "Código", "obra": "Obra", "partida": "Partida", "categoria": "Categoría",
    "presupuesto": "Presupuesto", "gastado": "Gastado", "disponible": "Disponible",
    "avance": "Avance", "pct_gastado": "% gastado", "desviacion": "Desviación",
    "proyeccion": "Proyección final", "sobrecosto_proyectado": "Sobrecosto proyectado",
    "partidas_en_rojo": "Partidas en rojo", "estado": "Estado",
}


def tabla(df: pd.DataFrame, columnas: list[str]):
    """Muestra un DataFrame con nombres bonitos y los números con formato."""
    vista = df[columnas].rename(columns=NOMBRES)
    formato = {c: f for c, f in FORMATO.items() if c in vista.columns}
    st.dataframe(vista.style.format(formato, na_rep="—"), hide_index=True, width="stretch")


def grafico_presupuesto_vs_gasto(df: pd.DataFrame, etiqueta: str):
    """Barra = lo gastado. Marca vertical = el presupuesto. Si la barra pasa la marca, se pasó."""
    base = alt.Chart(df).encode(y=alt.Y(f"{etiqueta}:N", sort=None, title=None,
                                        axis=alt.Axis(labelLimit=260)))
    detalle = [
        alt.Tooltip(f"{etiqueta}:N"),
        alt.Tooltip("presupuesto:Q", format=",.0f", title="Presupuesto (₡)"),
        alt.Tooltip("gastado:Q", format=",.0f", title="Gastado (₡)"),
        alt.Tooltip("avance:Q", format=".0%", title="Avance"),
        alt.Tooltip("estado:N", title="Estado"),
    ]
    barras = base.mark_bar(color=AZUL, size=14, cornerRadiusEnd=4).encode(
        x=alt.X("gastado:Q", title="Colones", axis=alt.Axis(format="~s")), tooltip=detalle)
    marcas = base.mark_tick(color=GRIS, thickness=3, size=26).encode(x="presupuesto:Q", tooltip=detalle)
    st.altair_chart((barras + marcas).properties(height=alt.Step(40)), width="stretch")
    st.caption("Barra azul = gastado · Marca gris = presupuesto")


def plantilla_excel() -> bytes:
    archivo = io.BytesIO()
    importar.escribir_excel(demo.generar(), archivo)
    return archivo.getvalue()


def cargar_demo(con):
    limpios, _, _ = importar.validar(demo.generar())
    importar.cargar(con, limpios)


# ------------------------------------------------------------------ datos

con = db.conectar()
if not db.hay_datos(con):          # primera vez: arranca con el ejemplo para que no se vea vacío
    cargar_demo(con)

with st.sidebar:
    st.header("Ajustes")
    tolerancia = st.slider(
        "Tolerancia de sobrecosto", 0, 30, 10, format="%d%%",
        help="Si la proyección final se pasa del presupuesto por menos de este porcentaje, "
             "la partida queda en amarillo. Si se pasa por más, en rojo.",
    ) / 100
    st.caption("Los datos precargados son **ficticios**, solo para demostración.")

partidas = calculos.metricas_partidas(db.consulta(con, "resumen_partidas"), tolerancia)
obras = calculos.resumen_obras(partidas, tolerancia)

# Mensaje pendiente de una acción anterior (guardar un gasto, por ejemplo).
# Se guarda en session_state porque st.rerun() vuelve a correr todo el archivo
# y lo que se haya escrito en pantalla antes se pierde.
if "mensaje" in st.session_state:
    st.toast(st.session_state.pop("mensaje"), icon="✅")

st.title("🏗️ Control de costos por obra")
st.caption("Presupuesto contra gasto real, comparado con el avance de cada partida.")

tab_resumen, tab_obra, tab_registrar, tab_datos, tab_ayuda = st.tabs(
    ["Resumen general", "Detalle por obra", "Registrar", "Cargar datos", "Cómo se calcula"])

# Texto del selector de obra -> id de la obra (lo usan dos pestañas).
opciones_obra = dict(zip(obras["obra_codigo"] + " · " + obras["obra"], obras["obra_id"]))

# ------------------------------------------------------------------ resumen general

with tab_resumen:
    presupuesto, gastado, proyeccion = obras["presupuesto"].sum(), obras["gastado"].sum(), obras["proyeccion"].sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Presupuesto total", colones(presupuesto))
    pct_total = gastado / presupuesto if presupuesto > 0 else float("nan")    # no dividir entre 0
    c2.metric("Gastado", colones(gastado), f"{pct(pct_total)} del presupuesto", delta_color="off", delta_arrow="off")
    c3.metric("Proyección final", colones(proyeccion), diferencia(proyeccion - presupuesto),
              delta_color="inverse")
    c4.metric("Obras en rojo", f"{(obras['estado'] == calculos.SOBRECOSTO).sum()} de {len(obras)}")

    st.subheader("Obras")
    tabla(obras, ["obra_codigo", "obra", "estado", "presupuesto", "gastado", "avance", "pct_gastado",
                  "desviacion", "proyeccion", "sobrecosto_proyectado", "partidas_en_rojo"])
    grafico_presupuesto_vs_gasto(obras, "obra")

    st.subheader("Partidas que más se desvían")
    st.caption("Las 10 partidas con mayor sobrecosto proyectado, entre todas las obras.")
    peores = partidas[partidas["sobrecosto_proyectado"] > 0].nlargest(10, "sobrecosto_proyectado")
    if peores.empty:
        st.success("Ninguna partida proyecta sobrecosto.")
    else:
        tabla(peores, ["obra_codigo", "partida", "estado", "presupuesto", "gastado", "avance",
                       "proyeccion", "sobrecosto_proyectado"])

# ------------------------------------------------------------------ detalle por obra

with tab_obra:
    obra_id = int(opciones_obra[st.selectbox("Obra", list(opciones_obra))])
    obra = obras[obras["obra_id"] == obra_id].iloc[0]
    de_la_obra = partidas[partidas["obra_id"] == obra_id]

    st.markdown(f"**Estado:** {obra['estado']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Presupuesto", colones(obra["presupuesto"]))
    c2.metric("Gastado", colones(obra["gastado"]), f"{pct(obra['pct_gastado'])} del presupuesto", delta_color="off", delta_arrow="off")
    c3.metric("Avance", pct(obra["avance"]))
    c4.metric("Proyección final", colones(obra["proyeccion"]),
              diferencia(obra["sobrecosto_proyectado"]), delta_color="inverse")

    st.subheader("Partidas")
    tabla(de_la_obra, ["partida", "categoria", "estado", "presupuesto", "gastado", "disponible", "avance",
                       "pct_gastado", "desviacion", "proyeccion"])
    grafico_presupuesto_vs_gasto(de_la_obra, "partida")

    izquierda, derecha = st.columns(2)
    with izquierda:
        st.subheader("Gasto acumulado por mes")
        mensual = db.consulta(con, "gasto_mensual")
        mensual = mensual[mensual["obra_id"] == obra_id]
        linea = alt.Chart(mensual).mark_line(color=AZUL, strokeWidth=2, point=alt.OverlayMarkDef(size=70)).encode(
            x=alt.X("mes:O", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("gasto_acumulado:Q", title="Colones", axis=alt.Axis(format="~s")),
            tooltip=[alt.Tooltip("mes:O", title="Mes"),
                     alt.Tooltip("gasto_mes:Q", format=",.0f", title="Gasto del mes (₡)"),
                     alt.Tooltip("gasto_acumulado:Q", format=",.0f", title="Acumulado (₡)")],
        )
        tope = alt.Chart(pd.DataFrame({"presupuesto": [obra["presupuesto"]]})).mark_rule(
            color=GRIS, strokeDash=[6, 4], strokeWidth=2).encode(y="presupuesto:Q")
        st.altair_chart(linea + tope, width="stretch")
        st.caption("Línea azul = gasto acumulado · Línea punteada = presupuesto de la obra")
    with derecha:
        st.subheader("Proveedores con más gasto")
        proveedores = db.consulta(con, "top_proveedores", (obra_id,))
        proveedores.columns = ["Proveedor", "Facturas", "Total"]
        st.dataframe(proveedores.style.format({"Total": colones}), hide_index=True, width="stretch")

    st.subheader("Gastos registrados")
    gastos = db.consulta(con, "gastos_detalle", (obra_id,))
    filtro = st.multiselect("Filtrar por partida", sorted(gastos["partida"].unique()))
    if filtro:
        gastos = gastos[gastos["partida"].isin(filtro)]
    gastos.columns = ["Fecha", "Partida", "Proveedor", "Documento", "Descripción", "Monto"]
    st.caption(f"{len(gastos)} gastos · total {colones(gastos['Monto'].sum())}")
    st.dataframe(gastos.style.format({"Monto": colones}, na_rep="—"), hide_index=True, width="stretch")

    # Se pasa una función (lambda) en vez del archivo: Streamlit solo la ejecuta
    # cuando alguien presiona el botón, en vez de armar el Excel en cada clic de la app.
    st.download_button(
        "Descargar reporte de esta obra (.xlsx)",
        lambda: exportar.reporte_obra_excel(obra, de_la_obra, gastos),
        f"reporte_{obra['obra_codigo']}.xlsx",
    )

# ------------------------------------------------------------------ registrar

with tab_registrar:
    st.caption("Para el día a día: anotar un gasto o actualizar el avance sin volver a subir el Excel.")
    obra_reg = int(opciones_obra[st.selectbox("Obra", list(opciones_obra), key="obra_registrar")])
    partidas_reg = partidas[partidas["obra_id"] == obra_reg]

    st.subheader("Nuevo gasto")
    # st.form agrupa los campos: la app no se vuelve a correr con cada tecla,
    # solo cuando se presiona el botón.
    with st.form("nuevo_gasto", clear_on_submit=True):
        ids = dict(zip(partidas_reg["partida"], partidas_reg["partida_id"]))
        c1, c2, c3 = st.columns([2, 1, 1])
        partida_sel = c1.selectbox("Partida", list(ids))
        # "Hoy" en hora de Costa Rica: un servidor en la nube suele estar en otra zona horaria.
        hoy = datetime.now(ZoneInfo("America/Costa_Rica")).date()
        fecha = c2.date_input("Fecha", hoy, format="DD/MM/YYYY")
        monto = c3.number_input("Monto (₡)", min_value=0.0, step=1000.0, format="%.0f")
        c1, c2 = st.columns(2)
        proveedor = c1.text_input("Proveedor")
        documento = c2.text_input("N.º de factura o documento")
        descripcion = st.text_input("Descripción")
        if st.form_submit_button("Guardar gasto", type="primary"):
            try:
                registro.agregar_gasto(con, int(ids[partida_sel]), fecha, monto, proveedor, documento, descripcion)
            except ValueError as e:
                st.error(str(e))
            else:
                st.session_state["mensaje"] = f"Gasto de {colones(monto)} guardado en {partida_sel}."
                st.rerun()

    st.subheader("Corregir o borrar gastos")
    st.caption("Cambiá las celdas que quieras o marcá **Borrar**, y después guardá. "
               "No se aplica nada hasta presionar el botón.")
    originales = db.consulta(con, "gastos_editables", (obra_reg,))
    originales["fecha"] = pd.to_datetime(originales["fecha"]).dt.date
    originales.insert(0, "borrar", False)
    editados = st.data_editor(
        originales,
        hide_index=True,
        width="stretch",
        key=f"gastos_{obra_reg}",
        disabled=["gasto_id", "partida"],
        column_config={
            "borrar": st.column_config.CheckboxColumn("Borrar", width="small"),
            "gasto_id": None,
            "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
            "partida": "Partida",
            "proveedor": "Proveedor",
            "documento": "Documento",
            "descripcion": "Descripción",
            "monto": st.column_config.NumberColumn("Monto (₡)", format="localized", min_value=0),
        },
    )
    if st.button("Guardar cambios en gastos"):
        a_borrar = editados.loc[editados["borrar"], "gasto_id"].tolist()
        # Una fila cambió si alguna de sus columnas es distinta a la original.
        # fillna("") para que dos celdas vacías cuenten como iguales.
        columnas = ["fecha", "proveedor", "documento", "descripcion", "monto"]
        distinta = (editados[columnas].fillna("") != originales[columnas].fillna("")).any(axis=1)
        cambiados = editados[distinta & ~editados["borrar"]]
        if not a_borrar and cambiados.empty:
            st.info("No hiciste ningún cambio.")
        else:
            try:
                registro.guardar_cambios_gastos(con, cambiados.to_dict("records"), a_borrar)
            except ValueError as e:
                st.error(str(e))
            else:
                st.session_state["mensaje"] = (f"{len(cambiados)} gasto(s) corregido(s) "
                                               f"y {len(a_borrar)} borrado(s).")
                st.rerun()

    st.subheader("Avance de las partidas")
    st.caption("Cambiá el porcentaje en la columna **Avance %** y guardá.")
    editable = partidas_reg[["partida_id", "partida", "presupuesto", "gastado"]].assign(
        avance_pct=(partidas_reg["avance"] * 100).round(1))
    editado = st.data_editor(
        editable,
        hide_index=True,
        width="stretch",
        key=f"avances_{obra_reg}",
        disabled=["partida", "presupuesto", "gastado"],     # solo se puede editar el avance
        column_config={
            "partida_id": None,                               # None = columna oculta
            "partida": "Partida",
            "presupuesto": st.column_config.NumberColumn("Presupuesto (₡)", format="localized"),
            "gastado": st.column_config.NumberColumn("Gastado (₡)", format="localized"),
            "avance_pct": st.column_config.NumberColumn("Avance %", min_value=0, max_value=100, step=1,
                                                        format="%.0f %%"),
        },
    )
    if st.button("Guardar avances"):
        # Solo se mandan a la base las partidas cuyo avance cambió.
        cambios = editado[editado["avance_pct"] != editable["avance_pct"]]
        if cambios.empty:
            st.info("No cambiaste ningún avance.")
        else:
            try:
                registro.actualizar_avances(
                    con, {int(i): a / 100 for i, a in zip(cambios["partida_id"], cambios["avance_pct"])})
            except ValueError as e:              # por ejemplo, una celda que quedó vacía
                st.error(str(e))
            else:
                st.session_state["mensaje"] = f"Avance actualizado en {len(cambios)} partida(s)."
                st.rerun()

# ------------------------------------------------------------------ cargar datos

with tab_datos:
    st.subheader("1. Descargá la plantilla")
    st.write("Es un Excel con tres hojas (**Obras**, **Presupuesto** y **Gastos**) que ya trae "
             "los datos de ejemplo. Borrá las filas de ejemplo y poné las tuyas, sin cambiar los encabezados.")
    st.download_button("Descargar plantilla (.xlsx)", plantilla_excel, "plantilla_costos.xlsx")

    st.subheader("2. Subí tu archivo")
    st.warning("Al cargar un archivo se **reemplazan** todos los datos que hay ahora.")
    archivo = st.file_uploader("Archivo de Excel", type=["xlsx"])
    if archivo is not None:
        try:
            limpios, errores, avisos = importar.validar(importar.leer_excel(archivo))
        except ValueError as e:      # faltan hojas
            limpios, errores, avisos = {}, [str(e)], []

        if errores:
            st.error(f"El archivo tiene {len(errores)} error(es). No se cargó nada. Corregilos y volvé a subirlo:")
            st.dataframe(pd.DataFrame({"Error": errores}), hide_index=True, width="stretch")
        else:
            st.success(f"Archivo válido: {len(limpios['Obras'])} obras, "
                       f"{len(limpios['Presupuesto'])} partidas y {len(limpios['Gastos'])} gastos.")
            for aviso in avisos:
                st.warning(aviso)
            if st.button("Cargar estos datos", type="primary"):
                importar.cargar(con, limpios)
                st.rerun()

    st.subheader("3. Respaldá tus datos")
    st.write("Descarga todo lo que hay en la herramienta (incluidos los gastos y avances registrados aquí) "
             "en el mismo formato de la plantilla. Ese archivo se puede volver a subir.")
    # La función corre en otro hilo, y una conexión de SQLite no se puede compartir
    # entre hilos: por eso abre su propia conexión con db.conectar().
    st.download_button("Descargar respaldo (.xlsx)", lambda: exportar.respaldo_excel(db.conectar()),
                       "respaldo_costos.xlsx")

    st.subheader("Volver a los datos de ejemplo")
    if st.button("Restaurar datos de ejemplo (ficticios)"):
        cargar_demo(con)
        st.rerun()

# ------------------------------------------------------------------ cómo se calcula

with tab_ayuda:
    st.markdown("""
### La idea
Ver solo *cuánto queda del presupuesto* engaña. Si una partida ya gastó el 60 % de su plata
pero va por el 40 % de avance, va mal aunque todavía tenga saldo. Por eso cada partida se
compara contra su **avance**.

### Indicadores
| Indicador | Fórmula | Qué dice |
|---|---|---|
| Disponible | presupuesto − gastado | Cuánta plata queda |
| % gastado | gastado ÷ presupuesto | Qué parte del presupuesto ya se usó |
| Costo esperado | presupuesto × avance | Lo que debería llevar gastado según el avance |
| Desviación | gastado − costo esperado | Positivo = va más caro de lo que el avance justifica |
| Proyección final | gastado ÷ avance | Lo que costará al terminar si sigue al mismo ritmo |
| Sobrecosto proyectado | proyección − presupuesto | Cuánto se pasaría al final |

### Semáforo
- 🟢 **En presupuesto**: la proyección final no supera el presupuesto.
- 🟡 **En riesgo**: lo supera, pero dentro de la tolerancia (ajustable en la barra lateral).
- 🔴 **Sobrecosto**: lo supera por más de la tolerancia.

### Limitaciones (para leer los números con criterio)
- La proyección asume que lo que falta costará al mismo ritmo que lo ya hecho. Con avances
  muy bajos (5–10 %) una sola factura grande la dispara: tomala como alerta, no como dato exacto.
- El avance lo digita una persona. Si el avance está mal estimado, todo lo demás también.
- Una partida sin avance se proyecta igual a su presupuesto (o a lo gastado, si ya lo superó).
""")
    st.subheader("Las consultas SQL que usa la herramienta")
    for nombre in ["resumen_partidas", "gasto_mensual", "top_proveedores", "gastos_detalle", "gastos_editables"]:
        with st.expander(f"sql/{nombre}.sql"):
            st.code(db.texto_sql(nombre), language="sql")
