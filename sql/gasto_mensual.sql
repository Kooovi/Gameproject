-- Gasto por mes de cada obra y su acumulado.
--
-- 1) La CTE "mensual" suma los gastos por obra y por mes.
-- 2) SUM(...) OVER (...) es una función de ventana: va sumando mes a mes
--    dentro de cada obra (PARTITION BY) sin colapsar las filas.

WITH mensual AS (
    SELECT
        p.obra_id,
        strftime('%Y-%m', g.fecha) AS mes,
        SUM(g.monto)               AS gasto_mes
    FROM gastos g
    JOIN partidas p ON p.id = g.partida_id
    GROUP BY p.obra_id, mes
)
SELECT
    obra_id,
    mes,
    gasto_mes,
    SUM(gasto_mes) OVER (PARTITION BY obra_id ORDER BY mes) AS gasto_acumulado
FROM mensual
ORDER BY obra_id, mes;
