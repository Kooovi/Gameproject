# Práctica de Power BI con los datos del proyecto

Armar en Power BI el mismo tablero que hace la app, con los datos de ejemplo. Sirve para
aprender Power BI con datos que ya entendés, y al final podés comparar tus números contra
los de la app.

**Ojo:** Power BI Desktop solo funciona en Windows. Desde Linux Mint las opciones son una
computadora con Windows (por ejemplo, un laboratorio de la U) o una máquina virtual.

## Los datos

Ya están en `powerbi/datos/` (son ficticios). Para regenerarlos:

```bash
python -m costos.powerbi             # datos de ejemplo
python -m costos.powerbi --actual    # lo que tengas cargado en la app
```

| Archivo | Una fila por | Columnas clave |
|---|---|---|
| `obras.csv` | obra | `obra_id`, `codigo`, `obra` |
| `partidas.csv` | partida | `partida_id`, `obra_id`, `presupuesto`, `avance` (0 a 1) |
| `gastos.csv` | gasto | `gasto_id`, `partida_id`, `fecha`, `proveedor`, `monto` |
| `calendario.csv` | día del año | `fecha`, `anio`, `mes`, `anio_mes`, `trimestre` |
| `verificacion.csv` | obra | lo que tienen que dar tus medidas |

## Paso 1. Cargar y relacionar

1. *Obtener datos* → *Texto o CSV* → cargar los cuatro primeros archivos.
2. En Power Query revisá los tipos: `fecha` como **Fecha** en `gastos` y en `calendario`;
   `presupuesto`, `avance` y `monto` como **Número decimal**.
3. En la vista de modelo, crear las relaciones (todas de uno a varios):

```
obras[obra_id]         1 ──── *  partidas[obra_id]
partidas[partida_id]   1 ──── *  gastos[partida_id]
calendario[fecha]      1 ──── *  gastos[fecha]
```

4. Marcar `calendario` como **tabla de fechas** (clic derecho → *Marcar como tabla de fechas*).

**¿Por qué una tabla de calendario?** Si se agrupa usando la fecha de `gastos`, los meses
sin gastos desaparecen y las funciones de tiempo (acumulados, mes anterior) fallan. El
calendario tiene todos los días, haya gastos o no.

**¿Por qué así y no todo en una tabla?** Es el mismo diseño de la base de datos: cada dato
vive en un solo lugar. Las tablas con montos (`gastos`) se llaman *tablas de hechos* y las
que describen (`obras`, `calendario`) se llaman *dimensiones*. Es lo que se conoce como
**modelo estrella**, y es la pregunta más común sobre Power BI en entrevistas.

## Paso 2. Las medidas DAX

Crear una tabla vacía llamada `Medidas` para tenerlas juntas (*Especificar datos* → Cargar).
Cada medida es una fórmula que se recalcula según los filtros activos: la misma medida
`Gastado` da el total general en una tarjeta y el total por obra en una tabla.

```dax
Presupuesto = SUM ( partidas[presupuesto] )

Gastado = SUM ( gastos[monto] )

% gastado = DIVIDE ( [Gastado], [Presupuesto] )

Costo esperado =
SUMX ( partidas, partidas[presupuesto] * partidas[avance] )

Desviación = [Gastado] - [Costo esperado]
```

`SUMX` recorre la tabla fila por fila, calcula la expresión en cada una y suma los
resultados. Es como agregar una columna auxiliar en Excel y sumarla, pero sin la columna.

La proyección es la más interesante:

```dax
Proyección final =
SUMX (
    partidas,
    VAR gastado_partida = CALCULATE ( SUM ( gastos[monto] ) )
    RETURN
        IF (
            partidas[avance] > 0,
            gastado_partida / partidas[avance],
            MAX ( partidas[presupuesto], gastado_partida )
        )
)

Sobrecosto proyectado = [Proyección final] - [Presupuesto]
```

- `VAR ... RETURN` guarda un resultado intermedio con nombre, para no repetirlo.
- `CALCULATE ( SUM ( gastos[monto] ) )` dentro de `SUMX` suma **solo los gastos de la
  partida de esa fila**. Esto se llama *transición de contexto*: `CALCULATE` convierte la
  fila actual en un filtro. Sin `CALCULATE` sumaría todos los gastos en cada fila.
- La regla es la misma de la app: si no hay avance, se asume el presupuesto (o lo gastado,
  si ya lo superó).

El semáforo, con la tolerancia del 10 %:

```dax
Estado =
VAR tolerancia = 0.10
RETURN
    SWITCH (
        TRUE (),
        [Proyección final] <= [Presupuesto], "🟢 En presupuesto",
        [Proyección final] <= [Presupuesto] * ( 1 + tolerancia ), "🟡 En riesgo",
        "🔴 Sobrecosto"
    )
```

`SWITCH ( TRUE (), ... )` es el SI anidado de DAX: devuelve el resultado de la primera
condición que se cumpla.

Gasto acumulado en el tiempo:

```dax
Gasto acumulado =
CALCULATE (
    [Gastado],
    FILTER ( ALL ( calendario[fecha] ), calendario[fecha] <= MAX ( calendario[fecha] ) )
)
```

`ALL` quita el filtro de fecha del gráfico, y `FILTER` vuelve a poner uno nuevo: "todas las
fechas hasta la de este punto del gráfico".

## Paso 3. Verificar

Hacé una tabla con `obras[codigo]` y las medidas `Presupuesto`, `Gastado`,
`Costo esperado`, `Proyección final` y `Sobrecosto proyectado`. Tiene que dar lo mismo
que `verificacion.csv` (puede variar en el último colón por redondeo):

| Obra | Presupuesto | Gastado | Proyección final |
|---|---|---|---|
| OB-01 | 78 000 000 | 57 905 100 | 73 945 641 |
| OB-02 | 215 000 000 | 97 959 100 | 226 066 449 |
| OB-03 | 42 000 000 | 43 953 700 | 49 707 283 |
| OB-04 | 340 000 000 | 25 995 400 | 344 016 825 |
| **Total** | **675 000 000** | **225 813 300** | **693 736 198** |

Si la proyección no coincide, el error casi siempre está en el `CALCULATE` (ver arriba).

**Cuidado:** si filtrás por fecha, `Gastado` cambia, pero el avance de las partidas no
(es el avance de hoy). Por eso la proyección solo tiene sentido sin filtro de fecha.

## Paso 4. El tablero

Página 1, **Resumen**:
- Tarjetas: Presupuesto, Gastado, Proyección final, Sobrecosto proyectado.
- Tabla por obra con todas las medidas y `Estado`.
- Gráfico de barras: `Gastado` y `Presupuesto` por obra.
- Segmentador de `categoria`.

Página 2, **Detalle**:
- Segmentador de obra.
- Tabla por partida con formato condicional en `Sobrecosto proyectado` (rojo si es positivo).
- Gráfico de líneas: `Gasto acumulado` por `calendario[anio_mes]`.
- Gráfico de barras: `Gastado` por `proveedor`, de mayor a menor.

## De Excel a Power BI

| En Excel | En Power BI |
|---|---|
| Tabla dinámica | Objeto visual *Matriz* |
| Segmentador | Segmentador (igual) |
| `BUSCARV` entre hojas | Relaciones del modelo |
| Columna con fórmula | Columna calculada (evitalas: preferí medidas) |
| `SUMAR.SI.CONJUNTO` | Una medida + los filtros del visual |
| `SI` anidado | `SWITCH ( TRUE (), ... )` |
| Limpiar datos a mano | Power Query (queda grabado y se repite solo) |

## Retos

1. Medida `CPI` = `DIVIDE ( [Costo esperado], [Gastado] )`. Menor que 1 = va caro.
2. Medida `Gasto mes anterior` usando `DATEADD ( calendario[fecha], -1, MONTH )`.
3. Medida que cuente las partidas en rojo de cada obra (pista: `COUNTROWS ( FILTER ( partidas, ... ) )`).
4. Un parámetro de *what-if* para cambiar la tolerancia del semáforo desde un control deslizante.
