-- Lista de gastos de una obra, del más reciente al más viejo.

SELECT
    g.fecha,
    p.nombre AS partida,
    g.proveedor,
    g.documento,
    g.descripcion,
    g.monto
FROM gastos g
JOIN partidas p ON p.id = g.partida_id
WHERE p.obra_id = ?
ORDER BY g.fecha DESC, g.id DESC;
