-- Práctica de SQL sobre la base del proyecto (obras, partidas, gastos).
--
-- Escribí tu consulta debajo de cada enunciado y revisá con:
--     python practica/revisar.py
--
-- Las columnas van en el orden que dice el enunciado. El nombre que les pongás no importa.
-- Las instrucciones completas están en practica/README.md.

-- [1] Todas las columnas de la tabla obras. Ordená por codigo.


-- [2] nombre y cliente de las obras que empezaron después del 31 de mayo de 2026. Ordená por fecha_inicio.


-- [3] Los 5 gastos de mayor monto: fecha, proveedor, monto. Ordená del más grande al más pequeño.


-- [4] Una sola fila con: cuántos gastos hay y cuánto suman.


-- [5] La lista de proveedores sin repetir. Ordená alfabéticamente.


-- [6] fecha y monto de los gastos de septiembre de 2026 mayores a 2 000 000. Ordená por monto de mayor a menor.


-- [7] nombre y presupuesto de las partidas terminadas (avance = 1) con presupuesto mayor a 10 000 000. Ordená por presupuesto de mayor a menor.


-- [8] Por proveedor: proveedor, cantidad de gastos y total pagado. Ordená por total de mayor a menor.


-- [9] proveedor y cantidad de gastos, solo de los proveedores con más de 20 gastos. Ordená por cantidad de mayor a menor.


-- [10] Cada partida con el nombre de su obra: nombre de la obra, nombre de la partida, presupuesto. Ordená por nombre de la obra y luego por presupuesto de mayor a menor.


-- [11] Total gastado por obra: codigo de la obra y total. Ordená por codigo.


-- [12] Las partidas que no tienen ningún gasto: codigo de la obra y nombre de la partida. Ordená por codigo y luego por nombre de la partida.


-- [13] Presupuesto por obra y por categoría: codigo, categoria, presupuesto total. Ordená por codigo y luego por categoria.


-- [14] Clasificá los gastos por tamaño: 'Pequeño' (menos de 500 000), 'Mediano' (menos de 3 000 000) o 'Grande'. Mostrá tamaño y cuántos hay de cada uno. Ordená por cantidad de mayor a menor.


-- [15] fecha y monto de los gastos que superan 4 veces el monto promedio. Ordená por monto de mayor a menor.


-- [16] Las partidas que ya gastaron más que su presupuesto: codigo de la obra, partida, presupuesto, gastado. Ordená por el exceso (gastado - presupuesto) de mayor a menor.


-- [17] El gasto más grande de cada obra: codigo, fecha, proveedor, monto. Ordená por codigo.


-- [18] Para la obra OB-01: partida, presupuesto y qué porcentaje del presupuesto de la obra representa (redondeado a 1 decimal). Ordená por porcentaje de mayor a menor.


-- [19] Para la obra OB-02: mes (AAAA-MM), gasto del mes y la diferencia contra el mes anterior (vacía en el primer mes). Ordená por mes.


-- [20] Reto. Por obra: codigo, presupuesto total, gastado total y porcentaje gastado (redondeado a 1 decimal). Ordená por codigo. Ojo: revisá que el presupuesto de OB-01 dé 78 000 000.

