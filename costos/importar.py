"""Importa los datos desde un Excel con tres hojas: Obras, Presupuesto y Gastos.

Flujo:  leer_excel()  ->  validar()  ->  cargar()

validar() no modifica la base: solo devuelve los datos limpios más una lista
de errores (impiden cargar) y de avisos (se carga, pero conviene revisarlos).
Cada mensaje dice la hoja y la fila de Excel, para que se pueda corregir.
"""

import re
import sqlite3
import unicodedata

import pandas as pd

# Columnas de cada hoja. Los encabezados se comparan sin mayúsculas, tildes ni
# espacios, así que "Código", "CODIGO" y " codigo " valen igual.
COLUMNAS = {
    "Obras": ["codigo", "nombre", "cliente", "fecha_inicio", "fecha_fin_prevista"],
    "Presupuesto": ["obra", "partida", "categoria", "presupuesto", "avance_pct"],
    "Gastos": ["fecha", "obra", "partida", "proveedor", "documento", "descripcion", "monto"],
}
OBLIGATORIAS = {
    "Obras": ["codigo", "nombre"],
    "Presupuesto": ["obra", "partida", "presupuesto"],
    "Gastos": ["fecha", "obra", "partida", "monto"],
}
NO_SON_TEXTO = {"presupuesto", "avance_pct", "monto", "fecha", "fecha_inicio", "fecha_fin_prevista", "fila"}
SIN_PRESUPUESTAR = "Sin presupuestar"
# Otras formas comunes de llamar a una columna -> el nombre que usa la herramienta.
ALIAS = {"avance": "avance_pct", "avance_%": "avance_pct", "%_avance": "avance_pct",
         "codigo_obra": "obra", "detalle": "descripcion", "factura": "documento",
         "fecha_fin": "fecha_fin_prevista"}


def leer_excel(archivo) -> dict[str, pd.DataFrame]:
    """Lee las tres hojas. Lanza ValueError si falta alguna."""
    hojas = pd.read_excel(archivo, sheet_name=None)  # None = todas las hojas, en un dict
    faltan = [h for h in COLUMNAS if h not in hojas]
    if faltan:
        raise ValueError(f"Al archivo le faltan las hojas: {', '.join(faltan)}")
    return {h: hojas[h] for h in COLUMNAS}


def _encabezado(nombre) -> str:
    """'  Código Obra ' -> 'codigo_obra'. Quita tildes, mayúsculas y espacios."""
    texto = unicodedata.normalize("NFKD", str(nombre).strip().lower())
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra))   # sin tildes
    texto = re.sub(r"\s+", "_", texto)
    return ALIAS.get(texto, texto)


def _texto(serie: pd.Series) -> pd.Series:
    """Pasa a texto sin espacios sobrantes; las celdas vacías quedan como NA."""
    def uno(valor):
        if pd.isna(valor):
            return pd.NA
        # Un código de obra "1" que Excel guardó como número llega como 1.0: se deja "1".
        if isinstance(valor, float) and valor.is_integer():
            valor = int(valor)
        return str(valor).strip() or pd.NA
    return serie.map(uno).astype("string")


def _numero(valor):
    """Convierte una celda a número. Devuelve None si no se puede.

    Acepta números de Excel y también texto como "₡1.250.000,50" o "1,250,000.50".
    Regla para el texto: si hay punto y coma, el último que aparece es el decimal.
    Si solo hay uno de los dos y agrupa de tres en tres ("1.250.000"), son miles.
    """
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = re.sub(r"[₡¢$%\s]|CRC", "", str(valor))
    if "." in texto and "," in texto:
        miles, decimal = (".", ",") if texto.rfind(",") > texto.rfind(".") else (",", ".")
        texto = texto.replace(miles, "").replace(decimal, ".")
    elif re.fullmatch(r"-?\d{1,3}([.,]\d{3})+", texto):
        texto = texto.replace(".", "").replace(",", "")          # separador de miles
    else:
        texto = texto.replace(",", ".")                          # coma decimal
    try:
        return float(texto)
    except ValueError:
        return None


def _numeros(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie.map(_numero), errors="coerce")


def _fechas(serie: pd.Series) -> pd.Series:
    """Convierte a fecha. Lo que no se pueda leer queda vacío (NaT).

    Si Excel ya trae la celda como fecha, se respeta. Si viene como texto, se
    prueba primero AAAA-MM-DD (inequívoco) y después día/mes/año, que es como
    se escribe en Costa Rica: "03/04/2026" es 3 de abril, no 4 de marzo.
    """
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie
    iso = pd.to_datetime(serie, format="%Y-%m-%d", errors="coerce")
    dia_primero = pd.to_datetime(serie, format="mixed", dayfirst=True, errors="coerce")
    return iso.fillna(dia_primero)


def validar(datos: dict[str, pd.DataFrame]):
    """Limpia y revisa los datos. Devuelve (datos_limpios, errores, avisos)."""
    errores, avisos, limpios = [], [], {}

    for hoja, columnas in COLUMNAS.items():
        df = datos[hoja].copy()
        df.columns = [_encabezado(c) for c in df.columns]
        faltan = [c for c in OBLIGATORIAS[hoja] if c not in df.columns]
        if faltan:
            errores.append(f"Hoja {hoja}: faltan las columnas {', '.join(faltan)}")
            continue
        for c in columnas:           # las opcionales que no vengan se crean vacías
            if c not in df.columns:
                df[c] = pd.NA
        df = df[columnas].dropna(how="all")
        # Fila tal como se ve en Excel: +2 por el encabezado y porque pandas cuenta desde 0.
        df["fila"] = df.index + 2
        limpios[hoja] = df

    if errores:                      # sin las columnas no tiene sentido seguir revisando
        return limpios, errores, avisos

    obras, pres, gastos = limpios["Obras"], limpios["Presupuesto"], limpios["Gastos"]

    def error(hoja, filas, mensaje):
        for fila in filas:
            errores.append(f"Hoja {hoja}, fila {fila}: {mensaje}")

    # --- Texto y obligatorios -------------------------------------------------
    for hoja, df in limpios.items():
        for c in df.columns:
            if c not in NO_SON_TEXTO:
                df[c] = _texto(df[c])
        for c in OBLIGATORIAS[hoja]:
            if c not in NO_SON_TEXTO:
                error(hoja, df.loc[df[c].isna(), "fila"], f"la columna '{c}' está vacía")

    # --- Números --------------------------------------------------------------
    # Lo que no se pueda leer como número queda vacío (NaN) y se reporta como error.
    pres["presupuesto"] = _numeros(pres["presupuesto"])
    error("Presupuesto", pres.loc[pres["presupuesto"].isna() | (pres["presupuesto"] < 0), "fila"],
          "el presupuesto debe ser un número mayor o igual a 0")

    pres["avance_pct"] = _numeros(pres["avance_pct"]).fillna(0)
    # Una celda con formato de porcentaje en Excel (35 %) se lee como 0.35.
    # Si ningún avance pasa de 1 y hay decimales, se asume que vienen así.
    con_decimales = (pres["avance_pct"] % 1 != 0).any()
    if pres["avance_pct"].between(0, 1).all() and con_decimales:
        pres["avance_pct"] = pres["avance_pct"] * 100
        avisos.append("Hoja Presupuesto: los avances venían como fracción (0.35) y se "
                      "leyeron como porcentaje (35 %). Revisá que sea correcto.")
    error("Presupuesto", pres.loc[~pres["avance_pct"].between(0, 100), "fila"],
          "avance_pct debe estar entre 0 y 100")

    gastos["monto"] = _numeros(gastos["monto"])
    error("Gastos", gastos.loc[gastos["monto"].isna(), "fila"], "el monto debe ser un número")

    # --- Fechas ---------------------------------------------------------------
    gastos["fecha"] = _fechas(gastos["fecha"])
    error("Gastos", gastos.loc[gastos["fecha"].isna(), "fila"], "la fecha está vacía o no es válida")
    for c in ("fecha_inicio", "fecha_fin_prevista"):
        obras[c] = _fechas(obras[c])

    # --- Duplicados -----------------------------------------------------------
    error("Obras", obras.loc[obras["codigo"].duplicated() & obras["codigo"].notna(), "fila"],
          "código de obra repetido")
    error("Presupuesto", pres.loc[pres.duplicated(["obra", "partida"]), "fila"],
          "partida repetida dentro de la misma obra")

    # --- Hojas vacías ---------------------------------------------------------
    # Sin obras o sin partidas no hay nada que mostrar. Gastos sí puede venir
    # vacía: una obra que apenas empieza todavía no tiene gastos.
    if obras.empty:
        errores.append("Hoja Obras: no tiene ninguna obra")
    if pres.empty:
        errores.append("Hoja Presupuesto: no tiene ninguna partida")

    # --- Referencias entre hojas ----------------------------------------------
    codigos = set(obras["codigo"].dropna())
    for hoja, df in (("Presupuesto", pres), ("Gastos", gastos)):
        error(hoja, df.loc[df["obra"].notna() & ~df["obra"].isin(codigos), "fila"],
              "la obra no existe en la hoja Obras")

    for codigo in obras["codigo"].dropna():
        if codigo not in set(pres["obra"]):
            avisos.append(f"Obra {codigo}: no tiene partidas en la hoja Presupuesto, "
                          f"así que no aparecerá en los reportes.")

    # Si en Gastos la partida está escrita con otra mayúscula ("techos" y "Techos"),
    # se usa la forma en que aparece en el presupuesto. casefold() es un lower() más estricto.
    forma_oficial = {(obra, str(partida).casefold()): partida
                     for obra, partida in zip(pres["obra"], pres["partida"]) if not pd.isna(partida)}
    gastos["partida"] = [
        partida if pd.isna(partida) else forma_oficial.get((obra, str(partida).casefold()), partida)
        for obra, partida in zip(gastos["obra"], gastos["partida"])
    ]
    gastos["partida"] = gastos["partida"].astype("string")

    # Gastos cuya partida no está en el presupuesto: no se rechazan, porque un
    # gasto que nadie presupuestó es justo lo que la herramienta debe destapar.
    # Se les crea una partida con presupuesto 0 y se avisa.
    presupuestadas = set(zip(pres["obra"], pres["partida"]))
    es_huerfano = [
        obra in codigos and not pd.isna(partida) and (obra, partida) not in presupuestadas
        for obra, partida in zip(gastos["obra"], gastos["partida"])
    ]
    huerfanos = gastos[es_huerfano]
    if not huerfanos.empty:
        # size() cuenta cuántos gastos hay en cada combinación obra + partida.
        conteo = huerfanos.groupby(["obra", "partida"], sort=False).size().reset_index(name="n")
        nuevas = conteo[["obra", "partida"]].assign(
            categoria=SIN_PRESUPUESTAR, presupuesto=0.0, avance_pct=0.0, fila=pd.NA
        )
        limpios["Presupuesto"] = pd.concat([pres, nuevas], ignore_index=True)
        for fila in conteo.itertuples():
            avisos.append(f"Obra {fila.obra}: {fila.n} gasto(s) en la partida '{fila.partida}', "
                          f"que no está en el presupuesto. Se cargó con presupuesto 0.")

    return limpios, errores, avisos


def _fecha_iso(valor):
    return None if pd.isna(valor) else pd.Timestamp(valor).strftime("%Y-%m-%d")


def _o_nada(valor):
    return None if pd.isna(valor) else str(valor)


def cargar(con: sqlite3.Connection, limpios: dict[str, pd.DataFrame]) -> None:
    """Reemplaza todo el contenido de la base por los datos ya validados.

    "with con:" abre una transacción: si algo falla a medio camino se deshace
    todo (rollback) y la base queda como estaba. Nunca queda a medias.
    """
    with con:
        con.execute("DELETE FROM gastos")
        con.execute("DELETE FROM partidas")
        con.execute("DELETE FROM obras")

        id_obra = {}
        for o in limpios["Obras"].itertuples():
            cur = con.execute(
                "INSERT INTO obras (codigo, nombre, cliente, fecha_inicio, fecha_fin_prevista) "
                "VALUES (?, ?, ?, ?, ?)",
                (o.codigo, o.nombre, _o_nada(o.cliente),
                 _fecha_iso(o.fecha_inicio), _fecha_iso(o.fecha_fin_prevista)),
            )
            id_obra[o.codigo] = cur.lastrowid  # el id que SQLite le asignó

        id_partida = {}
        for p in limpios["Presupuesto"].itertuples():
            cur = con.execute(
                "INSERT INTO partidas (obra_id, nombre, categoria, presupuesto, avance) "
                "VALUES (?, ?, ?, ?, ?)",
                (id_obra[p.obra], p.partida, _o_nada(p.categoria),
                 float(p.presupuesto), float(p.avance_pct) / 100),
            )
            id_partida[(p.obra, p.partida)] = cur.lastrowid

        con.executemany(
            "INSERT INTO gastos (partida_id, fecha, proveedor, documento, descripcion, monto) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (id_partida[(g.obra, g.partida)], _fecha_iso(g.fecha), _o_nada(g.proveedor),
                 _o_nada(g.documento), _o_nada(g.descripcion), float(g.monto))
                for g in limpios["Gastos"].itertuples()
            ],
        )


def escribir_excel(datos: dict[str, pd.DataFrame], destino) -> None:
    """Escribe las tres hojas en un Excel (se usa para generar la plantilla)."""
    with pd.ExcelWriter(destino, engine="openpyxl") as writer:
        for hoja, columnas in COLUMNAS.items():
            datos[hoja][columnas].to_excel(writer, sheet_name=hoja, index=False)
            for i, c in enumerate(columnas):
                writer.sheets[hoja].column_dimensions[chr(65 + i)].width = max(16, len(c) + 4)
