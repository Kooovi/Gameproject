# Práctica de SQL

20 ejercicios sobre la misma base del proyecto, de lo más básico a funciones de ventana.
Los datos son los de ejemplo (ficticios) y siempre son los mismos.

## Cómo se usa

1. Abrí `practica/ejercicios.sql` y escribí tu consulta debajo de un enunciado.
2. Revisá:

   ```bash
   python practica/revisar.py
   ```

   ```
   ✅  1  correcto
   ❌  2  devuelve 4 fila(s) y se esperaban 2
   ⏳  3  pendiente
   ```

3. Si un ejercicio sale mal, mirá qué devuelve tu consulta:

   ```bash
   python practica/revisar.py 2
   ```

El revisor compara **resultados**, no texto: si tu consulta devuelve lo correcto, vale
aunque esté escrita distinto a la solución. Las columnas tienen que ir en el orden del
enunciado (el nombre no importa), y cuando el enunciado dice "Ordená", el orden cuenta.

Las soluciones comentadas están en `practica/soluciones.sql`. Intentá cada ejercicio
al menos 10 minutos antes de abrirlas.

## Las tablas

```
obras     id, codigo, nombre, cliente, fecha_inicio, fecha_fin_prevista
partidas  id, obra_id → obras.id, nombre, categoria, presupuesto, avance (0 a 1)
gastos    id, partida_id → partidas.id, fecha, proveedor, documento, descripcion, monto
```

Las fechas son texto con formato `AAAA-MM-DD`. Un gasto no guarda la obra: se llega a
ella pasando por la partida.

## Explorar a mano

El revisor deja la base en `data/practica.db`:

```bash
sudo apt install sqlite3      # una sola vez
sqlite3 data/practica.db
sqlite> .headers on
sqlite> .mode column
sqlite> SELECT * FROM obras;
sqlite> .quit
```

## Qué se practica

| Ejercicios | Tema |
|---|---|
| 1 – 7 | `SELECT`, `WHERE`, `ORDER BY`, `LIMIT`, `DISTINCT`, `COUNT`, `SUM` |
| 8 – 9 | `GROUP BY` y `HAVING` |
| 10 – 13 | `JOIN` y `LEFT JOIN` |
| 14 – 15 | `CASE` y subconsultas |
| 16 | CTE (`WITH`) |
| 17 – 19 | Funciones de ventana: `ROW_NUMBER`, `SUM() OVER`, `LAG` |
| 20 | Reto: el error clásico de sumar después de un `JOIN` que duplica filas |

Nota: esto es SQLite. Casi todo es igual en PostgreSQL, MySQL o SQL Server; lo que más
cambia son las funciones de fecha (`strftime` es propia de SQLite).
