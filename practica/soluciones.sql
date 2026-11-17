-- SOLUCIONES de la práctica de SQL.
-- Intentá cada ejercicio antes de mirar aquí: se aprende escribiendo, no leyendo.
-- Casi siempre hay más de una forma correcta; el revisor compara resultados, no texto.

-- [1] Todas las columnas de la tabla obras. Ordená por codigo.
SELECT * FROM obras ORDER BY codigo;

-- [2] nombre y cliente de las obras que empezaron después del 31 de mayo de 2026. Ordená por fecha_inicio.
-- Las fechas están guardadas como texto AAAA-MM-DD, y en ese formato
-- comparar texto da lo mismo que comparar fechas.
SELECT nombre, cliente
FROM obras
WHERE fecha_inicio > '2026-05-31'
ORDER BY fecha_inicio;

-- [3] Los 5 gastos de mayor monto: fecha, proveedor, monto. Ordená del más grande al más pequeño.
SELECT fecha, proveedor, monto
FROM gastos
ORDER BY monto DESC
LIMIT 5;

-- [4] Una sola fila con: cuántos gastos hay y cuánto suman.
SELECT COUNT(*), SUM(monto) FROM gastos;

-- [5] La lista de proveedores sin repetir. Ordená alfabéticamente.
SELECT DISTINCT proveedor FROM gastos ORDER BY proveedor;

-- [6] fecha y monto de los gastos de septiembre de 2026 mayores a 2 000 000. Ordená por monto de mayor a menor.
-- BETWEEN incluye los dos extremos.
SELECT fecha, monto
FROM gastos
WHERE fecha BETWEEN '2026-09-01' AND '2026-09-30'
  AND monto > 2000000
ORDER BY monto DESC;

-- [7] nombre y presupuesto de las partidas terminadas (avance = 1) con presupuesto mayor a 10 000 000. Ordená por presupuesto de mayor a menor.
SELECT nombre, presupuesto
FROM partidas
WHERE avance = 1 AND presupuesto > 10000000
ORDER BY presupuesto DESC;

-- [8] Por proveedor: proveedor, cantidad de gastos y total pagado. Ordená por total de mayor a menor.
-- GROUP BY hace un grupo por proveedor; COUNT y SUM se calculan dentro de cada grupo.
SELECT proveedor, COUNT(*) AS n, SUM(monto) AS total
FROM gastos
GROUP BY proveedor
ORDER BY total DESC;

-- [9] proveedor y cantidad de gastos, solo de los proveedores con más de 20 gastos. Ordená por cantidad de mayor a menor.
-- WHERE filtra filas ANTES de agrupar; HAVING filtra grupos DESPUÉS de agrupar.
-- Como COUNT(*) solo existe después de agrupar, tiene que ir en HAVING.
SELECT proveedor, COUNT(*) AS n
FROM gastos
GROUP BY proveedor
HAVING COUNT(*) > 20
ORDER BY n DESC;

-- [10] Cada partida con el nombre de su obra: nombre de la obra, nombre de la partida, presupuesto. Ordená por nombre de la obra y luego por presupuesto de mayor a menor.
-- Las dos tablas tienen una columna "nombre": por eso se usan alias (o, p).
SELECT o.nombre, p.nombre, p.presupuesto
FROM partidas p
JOIN obras o ON o.id = p.obra_id
ORDER BY o.nombre, p.presupuesto DESC;

-- [11] Total gastado por obra: codigo de la obra y total. Ordená por codigo.
-- El gasto no guarda la obra: hay que llegar por la partida (gastos -> partidas -> obras).
SELECT o.codigo, SUM(g.monto) AS total
FROM gastos g
JOIN partidas p ON p.id = g.partida_id
JOIN obras o    ON o.id = p.obra_id
GROUP BY o.codigo
ORDER BY o.codigo;

-- [12] Las partidas que no tienen ningún gasto: codigo de la obra y nombre de la partida. Ordená por codigo y luego por nombre de la partida.
-- El LEFT JOIN conserva todas las partidas. Las que no tienen gastos quedan
-- con las columnas de "g" en NULL, y con eso se las atrapa.
SELECT o.codigo, p.nombre
FROM partidas p
JOIN obras o       ON o.id = p.obra_id
LEFT JOIN gastos g ON g.partida_id = p.id
WHERE g.id IS NULL
ORDER BY o.codigo, p.nombre;

-- [13] Presupuesto por obra y por categoría: codigo, categoria, presupuesto total. Ordená por codigo y luego por categoria.
-- Se puede agrupar por más de una columna: un grupo por cada combinación.
SELECT o.codigo, p.categoria, SUM(p.presupuesto) AS total
FROM partidas p
JOIN obras o ON o.id = p.obra_id
GROUP BY o.codigo, p.categoria
ORDER BY o.codigo, p.categoria;

-- [14] Clasificá los gastos por tamaño: 'Pequeño' (menos de 500 000), 'Mediano' (menos de 3 000 000) o 'Grande'. Mostrá tamaño y cuántos hay de cada uno. Ordená por cantidad de mayor a menor.
-- CASE es el SI anidado de Excel: se evalúa en orden y se queda con el primero que se cumple.
SELECT
    CASE
        WHEN monto < 500000  THEN 'Pequeño'
        WHEN monto < 3000000 THEN 'Mediano'
        ELSE 'Grande'
    END AS tamano,
    COUNT(*) AS n
FROM gastos
GROUP BY tamano
ORDER BY n DESC;

-- [15] fecha y monto de los gastos que superan 4 veces el monto promedio. Ordená por monto de mayor a menor.
-- La subconsulta entre paréntesis se calcula primero y devuelve un solo número.
SELECT fecha, monto
FROM gastos
WHERE monto > 4 * (SELECT AVG(monto) FROM gastos)
ORDER BY monto DESC;

-- [16] Las partidas que ya gastaron más que su presupuesto: codigo de la obra, partida, presupuesto, gastado. Ordená por el exceso (gastado - presupuesto) de mayor a menor.
-- La CTE calcula el gastado por partida; después se usa como si fuera una tabla.
WITH gastado_por_partida AS (
    SELECT partida_id, SUM(monto) AS gastado
    FROM gastos
    GROUP BY partida_id
)
SELECT o.codigo, p.nombre, p.presupuesto, t.gastado
FROM partidas p
JOIN obras o               ON o.id = p.obra_id
JOIN gastado_por_partida t ON t.partida_id = p.id
WHERE t.gastado > p.presupuesto
ORDER BY t.gastado - p.presupuesto DESC;

-- [17] El gasto más grande de cada obra: codigo, fecha, proveedor, monto. Ordená por codigo.
-- ROW_NUMBER numera los gastos dentro de cada obra, del más grande al más pequeño.
-- Después basta quedarse con el número 1. (No se puede filtrar por una función
-- de ventana en el mismo SELECT; por eso va dentro de una CTE.)
WITH numerados AS (
    SELECT
        o.codigo, g.fecha, g.proveedor, g.monto,
        ROW_NUMBER() OVER (PARTITION BY o.id ORDER BY g.monto DESC) AS puesto
    FROM gastos g
    JOIN partidas p ON p.id = g.partida_id
    JOIN obras o    ON o.id = p.obra_id
)
SELECT codigo, fecha, proveedor, monto
FROM numerados
WHERE puesto = 1
ORDER BY codigo;

-- [18] Para la obra OB-01: partida, presupuesto y qué porcentaje del presupuesto de la obra representa (redondeado a 1 decimal). Ordená por porcentaje de mayor a menor.
-- SUM(...) OVER () sin nada adentro suma todas las filas del resultado,
-- pero sin colapsarlas: cada fila conserva su detalle y además ve el total.
SELECT
    p.nombre,
    p.presupuesto,
    ROUND(100.0 * p.presupuesto / SUM(p.presupuesto) OVER (), 1) AS pct
FROM partidas p
JOIN obras o ON o.id = p.obra_id
WHERE o.codigo = 'OB-01'
ORDER BY pct DESC;

-- [19] Para la obra OB-02: mes (AAAA-MM), gasto del mes y la diferencia contra el mes anterior (vacía en el primer mes). Ordená por mes.
-- LAG trae el valor de la fila anterior según el orden indicado.
WITH mensual AS (
    SELECT strftime('%Y-%m', g.fecha) AS mes, SUM(g.monto) AS gasto_mes
    FROM gastos g
    JOIN partidas p ON p.id = g.partida_id
    JOIN obras o    ON o.id = p.obra_id
    WHERE o.codigo = 'OB-02'
    GROUP BY mes
)
SELECT mes, gasto_mes, gasto_mes - LAG(gasto_mes) OVER (ORDER BY mes) AS diferencia
FROM mensual
ORDER BY mes;

-- [20] Reto. Por obra: codigo, presupuesto total, gastado total y porcentaje gastado (redondeado a 1 decimal). Ordená por codigo. Ojo: revisá que el presupuesto de OB-01 dé 78 000 000.
-- LA TRAMPA: si se une partidas con gastos y se suma p.presupuesto, el presupuesto
-- de cada partida se repite una vez por cada gasto y el total sale inflado.
-- La salida es sumar cada cosa por separado (dos CTE) y unir los totales al final.
WITH presupuestos AS (
    SELECT obra_id, SUM(presupuesto) AS presupuesto
    FROM partidas
    GROUP BY obra_id
),
gastados AS (
    SELECT p.obra_id, SUM(g.monto) AS gastado
    FROM gastos g
    JOIN partidas p ON p.id = g.partida_id
    GROUP BY p.obra_id
)
SELECT
    o.codigo,
    pr.presupuesto,
    ga.gastado,
    ROUND(100.0 * ga.gastado / pr.presupuesto, 1) AS pct_gastado
FROM obras o
JOIN presupuestos pr ON pr.obra_id = o.id
JOIN gastados ga     ON ga.obra_id = o.id
ORDER BY o.codigo;
