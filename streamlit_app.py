"""Interfaz web (Streamlit). Se corre con:  streamlit run streamlit_app.py

Este archivo solo dibuja la pantalla. La lógica vive en el paquete costos/:
  - costos/db.py        consultas SQL -> DataFrames
  - costos/calculos.py  indicadores con pandas
  - costos/importar.py  Excel -> validación -> base de datos
"""

import io

import altair as alt
import pandas as pd
import streamlit as st

from costos import calculos, db, demo, importar

AZUL = "#2a78d6"   # lo gastado
GRIS = "#6f6e69"   # la referencia (presupuesto)

st.set_page_config(page_title="Control de costos por obra", page_icon="🏗️", layout="wide")


# ------------------------------------------------------------------ utilidades

def colones(x) -> str:
    """Formato de moneda. El signo va antes del símbolo: -₡1,500."""
    if pd.isna(x):
        return "—"
    return f"{'-' if x < 0 else ''}₡{abs(x):,.0f}"


def diferencia(x) -> str:
    """Igual que colones() pero con + explícito, para que st.metric sepa si subió o bajó."""
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
    st.dataframe(vista.style.format(formato), hide_index=True, width="stretch")


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

st.title("🏗️ Control de costos por obra")
st.caption("Presupuesto contra gasto real, comparado con el avance de cada partida.")

tab_resumen, tab_obra, tab_datos, tab_ayuda = st.tabs(
    ["Resumen general", "Detalle por obra", "Cargar datos", "Cómo se calcula"])

# ------------------------------------------------------------------ resumen general

with tab_resumen:
    presupuesto, gastado, proyeccion = obras["presupuesto"].sum(), obras["gastado"].sum(), obras["proyeccion"].sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Presupuesto total", colones(presupuesto))
    c2.metric("Gastado", colones(gastado), f"{pct(gastado / presupuesto)} del presupuesto", delta_color="off", delta_arrow="off")
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
    opciones = dict(zip(obras["obra_codigo"] + " · " + obras["obra"], obras["obra_id"]))
    obra_id = int(opciones[st.selectbox("Obra", list(opciones))])
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
    st.dataframe(gastos.style.format({"Monto": colones}), hide_index=True, width="stretch")

# ------------------------------------------------------------------ cargar datos

with tab_datos:
    st.subheader("1. Descargá la plantilla")
    st.write("Es un Excel con tres hojas (**Obras**, **Presupuesto** y **Gastos**) que ya trae "
             "los datos de ejemplo. Borrá las filas de ejemplo y poné las tuyas, sin cambiar los encabezados.")
    plantilla = io.BytesIO()
    importar.escribir_excel(demo.generar(), plantilla)
    st.download_button("Descargar plantilla (.xlsx)", plantilla.getvalue(), "plantilla_costos.xlsx")

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
    for nombre in ["resumen_partidas", "gasto_mensual", "top_proveedores", "gastos_detalle"]:
        with st.expander(f"sql/{nombre}.sql"):
            st.code(db.texto_sql(nombre), language="sql")
