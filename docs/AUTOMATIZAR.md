# Automatizar el resumen de alertas

`costos/alertas.py` arma un resumen corto de las obras que van mal, listo para pegar
en WhatsApp o en un correo:

```bash
python -m costos.alertas --actual
```

```
*Control de costos · 17/11/2026*

🔴 *OB-03* Remodelación local comercial Escazú
   Avance 88% · gastado ₡44,0 M de ₡42,0 M
   Proyecta ₡49,7 M (+18% sobre el presupuesto)
   • Estructura y paredes: +₡1,8 M
   • Reparación de fuga: +₡1,4 M
   ...
1 en rojo, 2 en riesgo, de 4 obras.
```

(Sin `--actual` usa los datos de ejemplo, que son ficticios.)

## Programarlo con cron (Linux)

`cron` es el programador de tareas de Linux: corre un comando a la hora que le digás.

1. Abrí la lista de tareas:

   ```bash
   crontab -e
   ```

2. Agregá una línea al final (ajustá la ruta a donde tengás el proyecto):

   ```
   0 7 * * 1  cd ~/control-costos && python3 -m costos.alertas --actual > ~/alertas_costos.txt 2>&1
   ```

   Los cinco primeros campos son *minuto hora día-del-mes mes día-de-la-semana*.
   `0 7 * * 1` = a las 7:00, todos los lunes. `>` guarda lo que imprime en un archivo;
   `2>&1` guarda también los errores, para poder ver qué pasó si algo falla.

3. Para comprobar que quedó: `crontab -l`.

Si instalaste las librerías en un entorno virtual, en vez de `python3` poné la ruta al
Python de ese entorno, por ejemplo `~/control-costos/.venv/bin/python`.

**Limitación:** cron solo corre si la computadora está encendida a esa hora.

## Siguientes pasos (no están hechos)

Ideas para seguir con el paso 4 de tu plan, de más fácil a más difícil:

1. **Mandarlo por correo.** Python trae `smtplib` para enviar correos. Con Gmail hace
   falta una *contraseña de aplicación* (no la contraseña normal), y esa contraseña va
   en una variable de entorno, nunca escrita en el código ni subida a GitHub.
2. **Mandarlo solo si cambió algo.** Guardar el resumen anterior en un archivo y enviar
   únicamente cuando una obra cambia de color.
3. **Que una IA lo comente.** Mandar el resumen a la API de un modelo de lenguaje
   (por ejemplo, Claude) para que redacte un párrafo con posibles causas y qué revisar.
   La regla importante: el modelo comenta, pero los números siempre salen del código,
   para que no pueda inventarlos.
