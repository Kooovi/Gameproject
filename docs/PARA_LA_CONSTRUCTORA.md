# Cómo probar la herramienta con una obra real

Guía para conseguir los datos de **una obra ya terminada** y probar la herramienta con
ellos. Se usa una obra vieja a propósito: así se puede comparar lo que dice la herramienta
con lo que de verdad pasó, sin riesgo para una obra en curso.

## Qué datos hacen falta

No hace falta todo. Con esto alcanza:

| Dato | Dónde suele estar | Obligatorio |
|---|---|---|
| Presupuesto por partida (Cimientos, Techos, etc.) | El presupuesto que se le presentó al cliente | Sí |
| Cada gasto: fecha, monto y a qué partida corresponde | Control de facturas, planillas, caja chica | Sí |
| Proveedor y número de factura de cada gasto | El mismo control de facturas | No, pero ayuda |
| Avance de cada partida en algún momento de la obra | Informes de avance o bitácora | No (sin esto, la proyección no sirve) |

Si los gastos no están asignados a partidas, el ejercicio sirve igual: se asigna una
categoría aproximada y eso ya muestra algo útil.

## Cómo pasarlo a la plantilla

1. En la herramienta, pestaña **Cargar datos** → **Descargar plantilla**.
2. Borrar las filas de ejemplo de las tres hojas (dejando los encabezados).
3. Llenar:
   - **Obras**: una fila. Código corto (`OB-2024-01`) y nombre.
   - **Presupuesto**: una fila por partida, con el mismo código de obra.
     `avance_pct` puede quedar vacío.
   - **Gastos**: una fila por factura o pago. La columna `partida` tiene que decir
     exactamente lo mismo que en la hoja Presupuesto (las mayúsculas no importan).
4. Subir el archivo. Si algo está mal, la herramienta dice en qué hoja y fila.

No hace falta limpiar el formato: acepta montos como `₡1.250.000,50`, fechas como
`15/03/2024` y encabezados con tildes o mayúsculas.

**Atajo:** copiar y pegar columnas desde el Excel original suele ser más rápido que
digitar. Si el Excel original tiene otra forma, se puede escribir un script que lo
convierta; para eso hace falta ver un ejemplo del archivo.

## Privacidad

La herramienta corre en la computadora de quien la usa. Los datos quedan en el archivo
`data/costos.db` de esa computadora y **no se suben a internet**. No se deben subir datos
reales a una versión publicada en internet (ver `docs/PUBLICAR.md`).

Si los datos se comparten para hacer la prueba, se pueden anonimizar antes: cambiar el
nombre del cliente y de los proveedores no afecta ningún cálculo.

## Preguntas para hacer después de la prueba

Estas respuestas son las que sirven para mejorar la herramienta y para un testimonio:

1. ¿Lo que muestra coincide con lo que pasó en la obra? ¿Qué partidas se pasaron de verdad?
2. ¿Esto lo habría avisado a tiempo? ¿En qué mes se habría visto el problema?
3. ¿Qué dato le falta para que le sirva en una obra en curso?
4. ¿Cuánto tiempo le toma hoy armar este mismo análisis a mano?
5. ¿La usaría con las 4 obras activas? ¿Qué tendría que cambiar?

## Mensaje de ejemplo

Para pedir los datos (ajustalo a tu forma de hablar):

> Pa, terminé una primera versión de la herramienta para comparar presupuesto contra
> gasto por obra. Para probarla necesito los datos de una obra que ya esté terminada:
> el presupuesto por partida y la lista de facturas o gastos. No importa si está
> desordenado, yo lo acomodo. Los datos no salen de mi compu, y si querés le cambio
> los nombres de clientes y proveedores. Después te enseño lo que sale y me decís si
> coincide con lo que pasó en la obra.
