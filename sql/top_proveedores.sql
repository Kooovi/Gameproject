-- Proveedores a los que más se les ha pagado en una obra.
-- El "?" es un parámetro: el valor lo pasa Python, nunca se pega a mano
-- en el texto (así se evita la inyección de SQL).

SELECT
    COALESCE(g.proveedor, '(sin proveedor)') AS proveedor,
    COUNT(*)                                 AS n_gastos,
    SUM(g.monto)                             AS total
FROM gastos g
JOIN partidas p ON p.id = g.partida_id
WHERE p.obra_id = ?
GROUP BY 1
ORDER BY total DESC
LIMIT 10;
