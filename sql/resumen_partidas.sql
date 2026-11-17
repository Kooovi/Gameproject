-- Presupuesto contra gasto real, una fila por partida.
--
-- LEFT JOIN (y no INNER JOIN) porque una partida sin gastos todavía
-- tiene que aparecer en el reporte, con gastado = 0.
-- COALESCE convierte el NULL que deja el LEFT JOIN en un 0.

SELECT
    o.id                       AS obra_id,
    o.codigo                   AS obra_codigo,
    o.nombre                   AS obra,
    p.id                       AS partida_id,
    p.nombre                   AS partida,
    p.categoria,
    p.presupuesto,
    p.avance,
    COALESCE(SUM(g.monto), 0)  AS gastado,
    COUNT(g.id)                AS n_gastos
FROM partidas p
JOIN obras o       ON o.id = p.obra_id
LEFT JOIN gastos g ON g.partida_id = p.id
GROUP BY p.id
ORDER BY o.codigo, p.id;
