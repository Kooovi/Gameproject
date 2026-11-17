# Cómo presentar este proyecto en una entrevista

Antes de usar esto, asegurate de poder explicar cada parte con tus palabras (ver
`docs/GUIA.md` y hacer la práctica de `practica/`). Si te preguntan algo del código que
no entendés, se nota.

## Versión de 30 segundos

> Hice una herramienta para constructoras pequeñas que compara el presupuesto contra el
> gasto real de cada obra. La idea salió de ver que mi papá, que es ingeniero, maneja
> cuatro obras en Excel y le cuesta ver a tiempo cuáles se están pasando. La herramienta
> lee los datos desde Excel, los valida, los guarda en una base de datos y muestra un
> semáforo por obra y por partida, con una proyección de cuánto va a costar al terminar.

## Versión de 2 minutos

Usá la estructura **situación → problema → qué hice → resultado**:

1. **Situación.** Las constructoras pequeñas llevan el control de costos en Excel, un
   archivo por obra.
2. **Problema.** Con varias obras a la vez cuesta ver si el gasto va de acuerdo al
   presupuesto. Y ver solo el saldo engaña: una partida puede tener plata pero ir mal,
   si ya gastó más de lo que su avance justifica.
3. **Qué hice.**
   - Una base de datos con obras, partidas y gastos, y consultas SQL para cruzarlos.
   - Indicadores calculados con pandas: desviación contra el avance y una proyección del
     costo final, parecido al método de valor ganado de gestión de proyectos.
   - Carga desde una plantilla de Excel que valida los datos y dice en qué fila hay errores.
   - Una interfaz web con Streamlit, y pruebas automáticas.
4. **Resultado.** *(Decí solo lo que sea verdad en ese momento.)* Hoy funciona con datos
   de ejemplo y está listo para probarse con los datos de una obra terminada.
   Cuando lo pruebes con datos reales, aquí va lo que encontraste.

## In English (30 seconds)

> I built a cost-control tool for small construction companies. It compares each
> project's budget against actual spending, line by line. I got the idea from my dad, a
> civil engineer who manages four projects in Excel and struggles to spot overruns in
> time. The tool imports data from Excel, validates it, stores it in a SQL database, and
> shows a traffic-light status for each project, plus a forecast of the final cost.

Palabras útiles: *budget* (presupuesto), *actual cost* (gasto real), *cost overrun*
(sobrecosto), *line item* (partida), *progress* (avance), *forecast* (proyección),
*earned value* (valor ganado), *data validation*, *dashboard*.

## Preguntas probables y cómo responder

**¿Por qué no lo dejaste en Excel?**
Con un archivo por obra no hay una vista de todas juntas, y las fórmulas se rompen al
copiar filas. Aquí los datos están en un solo lugar y la base rechaza datos imposibles.
Pero sigo usando Excel como entrada, porque es lo que la gente ya sabe usar.

**¿Cómo calculás si una partida va mal?**
Comparo lo gastado contra lo que *debería* llevar gastado según el avance:
presupuesto × avance. Si gastó más, va cara. Y proyecto el costo final dividiendo lo
gastado entre el avance. Ejemplo: presupuesto 100, avance 40 %, gastado 60 → debería
llevar 40, lleva 20 de más, y al ritmo actual terminaría costando 150.

**¿Qué debilidad tiene?**
La proyección asume que lo que falta cuesta al mismo ritmo que lo hecho, y depende de
que el avance esté bien estimado, porque lo digita una persona. Con poco avance es poco
confiable. Por eso lo presento como alerta, no como pronóstico exacto.

**Explicame un `LEFT JOIN`.**
Une dos tablas pero conserva todas las filas de la primera aunque no tengan pareja.
Lo uso para que una partida sin gastos siga apareciendo en el reporte, con gastado = 0.

**¿Qué pasa si suben un Excel con errores?**
No se carga nada. Se muestra una lista con la hoja y la fila de cada error. Y la carga
es una transacción: si falla a la mitad, la base queda como estaba.

**¿Cómo sabés que los cálculos están bien?**
Tiene pruebas automáticas con casos calculados a mano, y una prueba que compara lo que
suma SQL contra sumar la hoja de gastos directamente. Corren solas en GitHub cada vez
que subo cambios.

**¿Lo usó alguien?** *(Respondé con la verdad del momento.)*
Todavía no. El siguiente paso es probarlo con los datos de una obra terminada.

## Sobre la ayuda de la IA

El código se escribió con ayuda de Claude Code. Si te preguntan, decilo sin rodeos:
hoy es una forma normal de trabajar, y lo que importa es que vos definiste el problema,
tomaste las decisiones y entendés el resultado. Algo como:

> Lo construí con un asistente de programación con IA. Yo definí qué tenía que hacer,
> revisé el código y lo probé. Después hice ejercicios de SQL y pandas sobre la misma
> base para dominar lo que usa.

Lo que no conviene es decir que lo escribiste todo solo, ni no poder explicar una parte.

## Qué mostrar en pantalla (si te dejan)

1. El resumen general: el semáforo y la obra en rojo.
2. El detalle de la obra en rojo: qué partidas la empujan.
3. Subir un Excel con un error a propósito, para mostrar el mensaje con hoja y fila.
4. Una consulta SQL de la carpeta `sql/`, explicada.
