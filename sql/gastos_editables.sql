-- Gastos de una obra con su id, para poder corregirlos o borrarlos desde la app.
-- Se diferencia de gastos_detalle.sql en que incluye g.id (sin el id no se sabe
-- qué fila de la base hay que cambiar).

SELECT
    g.id      AS gasto_id,
    g.fecha,
    p.nombre  AS partida,
    g.proveedor,
    g.documento,
    g.descripcion,
    g.monto
FROM gastos g
JOIN partidas p ON p.id = g.partida_id
WHERE p.obra_id = ?
ORDER BY g.fecha DESC, g.id DESC;
