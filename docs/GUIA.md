# Guía del código

Para entender el proyecto y poder explicarlo en una entrevista. Leelo con el código al lado.

## 1. El recorrido de un dato

```
Excel  ──leer_excel()──▶  DataFrames  ──validar()──▶  datos limpios  ──cargar()──▶  SQLite
                                                                                      │
pantalla  ◀── streamlit_app.py ◀── calculos.py (pandas) ◀── db.consulta() (SQL) ◀─────┘
```

Cada archivo hace **una sola cosa**. Eso se llama *separación de responsabilidades*: si
mañana se cambia Streamlit por otra interfaz, `costos/` no se toca; si cambia una fórmula,
solo se toca `calculos.py`.

## 2. La base de datos (`costos/esquema.sql`)

Tres tablas con relación **uno a muchos**:

```
obras 1 ──── N partidas 1 ──── N gastos
```

- `PRIMARY KEY`: el identificador único de cada fila.
- `REFERENCES obras(id)`: **llave foránea**. Una partida no puede apuntar a una obra que no existe.
- `UNIQUE (obra_id, nombre)`: no se puede repetir una partida dentro de la misma obra.
- `CHECK (avance BETWEEN 0 AND 1)`: la base rechaza valores imposibles aunque el programa falle.

**¿Por qué el gasto apunta a la partida y no a la obra?** Porque la partida ya sabe de qué
obra es. Guardar la obra también en el gasto sería repetir el dato, y un dato repetido se
puede contradecir. Eso es *normalizar*.

**¿Por qué SQLite?** Es un solo archivo, no hay que instalar servidor, y para el volumen de
una constructora pequeña sobra. Si creciera a varios usuarios escribiendo a la vez, se
pasaría a PostgreSQL; el SQL casi no cambia.

## 3. Las consultas (`sql/`)

### `resumen_partidas.sql` — la más importante

```sql
FROM partidas p
JOIN obras o       ON o.id = p.obra_id
LEFT JOIN gastos g ON g.partida_id = p.id
GROUP BY p.id
```

- `JOIN` pega cada partida con su obra.
- `LEFT JOIN` pega los gastos, pero **conserva las partidas que no tienen ninguno**. Con un
  `JOIN` normal esas partidas desaparecerían del reporte.
- `GROUP BY p.id` deja una fila por partida; `SUM(g.monto)` suma sus gastos.
- `COALESCE(SUM(g.monto), 0)`: si no hay gastos la suma da `NULL`; `COALESCE` lo cambia por 0.
- `COUNT(g.id)` y no `COUNT(*)`: `COUNT(*)` contaría 1 para una partida sin gastos (la fila
  vacía del `LEFT JOIN`); `COUNT(g.id)` ignora los `NULL` y da 0.

### `gasto_mensual.sql` — CTE y función de ventana

- `WITH mensual AS (...)` es una **CTE**: una consulta con nombre que se usa abajo, como
  una tabla temporal. Sirve para hacer las cosas por pasos.
- `SUM(gasto_mes) OVER (PARTITION BY obra_id ORDER BY mes)` es una **función de ventana**:
  calcula el acumulado mes a mes, reiniciando en cada obra, **sin** juntar las filas
  (a diferencia de `GROUP BY`).

### `top_proveedores.sql` — parámetros

`WHERE p.obra_id = ?` — el `?` lo llena Python al ejecutar. Nunca se arma el SQL pegando
texto (`"... = " + valor`), porque eso permite **inyección de SQL**.

## 4. Los cálculos (`costos/calculos.py`)

Ejemplo con números: una partida con presupuesto de ₡100, avance 40 % y ₡60 gastados.

| Indicador | Cuenta | Resultado |
|---|---|---|
| Costo esperado | 100 × 0,40 | ₡40 |
| Desviación | 60 − 40 | ₡20 de más |
| Proyección final | 60 ÷ 0,40 | ₡150 |
| Sobrecosto proyectado | 150 − 100 | ₡50 (50 %) → 🔴 |

Este mismo ejemplo es la primera prueba en `tests/test_costos.py`.

Detalles de pandas que vale la pena entender:

- **Operaciones por columna**: `df["presupuesto"] - df["gastado"]` resta todas las filas de
  un solo golpe, como arrastrar una fórmula en Excel.
- **`.where(condición)`**: deja el valor donde se cumple la condición y pone vacío (`NaN`)
  donde no. Se usa para no dividir entre cero.
- **`.fillna(otra_columna)`**: rellena los vacíos. Así se resuelve el caso "sin avance".
- **`groupby(...).agg(...)`**: lo mismo que una tabla dinámica: agrupa por obra y suma.
- **Avance ponderado**: el avance de la obra no es el promedio simple de las partidas,
  porque una partida de ₡50 millones pesa más que una de ₡2 millones.

Esta forma de medir se parece al **valor ganado** (*Earned Value*) de gestión de proyectos:
el "costo esperado" es el valor ganado (EV), lo gastado es el costo real (AC) y la
proyección es la estimación al terminar (EAC = presupuesto ÷ CPI).

## 5. La importación (`costos/importar.py`)

- `pd.read_excel(archivo, sheet_name=None)` lee **todas** las hojas y devuelve un diccionario.
- `pd.to_numeric(..., errors="coerce")` convierte a número; lo que no se puede queda como
  `NaN` en vez de botar el programa. Después se reportan esas filas como error.
- **Errores contra avisos**: un error (monto que no es número, obra que no existe) impide
  cargar. Un aviso (gasto en partida no presupuestada) deja cargar pero lo señala.
- **Transacción**: `with con:` hace que la carga sea todo o nada. Si falla a la mitad, la
  base vuelve a como estaba.

## 6. Las pruebas (`tests/`)

Cada prueba arma un caso pequeño, calculable a mano, y verifica el resultado con `assert`.
Sirven para cambiar el código sin miedo: si algo se rompe, `pytest` avisa.

La última prueba hace el recorrido completo: genera el Excel de ejemplo, lo lee, lo valida,
lo carga y comprueba que **lo que suma SQL es igual a sumar la hoja de gastos directamente**.

## 7. Preguntas que te pueden hacer

1. **¿Por qué no lo dejaste en Excel?** Con varias obras, cada una en su archivo, no hay una
   vista de todas juntas, y las fórmulas se rompen al copiar. Aquí los datos están en un
   solo lugar con reglas que impiden datos inválidos. Igual se respeta Excel como entrada,
   porque es lo que la gente ya usa.
2. **¿Qué diferencia hay entre `JOIN` y `LEFT JOIN`?** Ver sección 3.
3. **¿Qué pasa si suben un Excel con errores?** No se carga nada y se muestra la lista de
   errores con hoja y fila.
4. **¿Qué debilidad tiene la proyección?** Asume ritmo constante y depende del avance, que
   es una estimación humana. Con poco avance es poco confiable.
5. **¿Qué le mejorarías?** Ver "Próximos pasos" en el README.

## 8. Para practicar

Ejercicios cortos sobre este mismo proyecto (de más fácil a más difícil):

1. **SQL**: escribí una consulta que dé el total gastado por `categoria` en cada obra.
2. **SQL**: listá las partidas que no tienen ningún gasto (pista: `LEFT JOIN` + `WHERE g.id IS NULL`).
3. **SQL**: el gasto más grande de cada obra (pista: `ROW_NUMBER() OVER (PARTITION BY ...)`).
4. **pandas**: en `calculos.py`, agregá la columna `cpi` = costo esperado ÷ gastado, y una prueba.
5. **Streamlit**: agregá en "Detalle por obra" un gráfico del gasto por categoría.

Para probar consultas a mano:

```bash
sqlite3 data/costos.db
sqlite> .headers on
sqlite> .mode column
sqlite> SELECT * FROM obras;
```
