# Cómo publicar la app (Streamlit Community Cloud)

Es gratis y deja la app en un enlace tipo `https://tu-app.streamlit.app`, útil para el
portafolio y el currículum. **Todavía no está hecho**: estos son los pasos.

## Pasos

1. Unir la rama de trabajo a `main` en GitHub (con un pull request).
2. Entrar a <https://share.streamlit.io> con la cuenta de GitHub.
3. *Create app* → elegir el repositorio, la rama `main` y el archivo `streamlit_app.py`.
4. *Deploy*. La primera vez tarda un par de minutos instalando `requirements.txt`.

Cada vez que se suba un cambio a `main`, la app se actualiza sola.

## Lo que hay que saber antes

Publicada así sirve como **demostración con datos ficticios, no para datos reales**:

- **Cualquiera con el enlace puede ver y cambiar los datos.** No hay usuarios ni contraseñas.
  No subás ahí el Excel real de una constructora.
- **Los datos no son permanentes.** La base es un archivo SQLite dentro del servidor, y
  Streamlit Cloud reinicia el servidor cuando la app pasa un tiempo sin uso o se actualiza.
  Al reiniciar, vuelve a los datos de ejemplo.
- **Todos los visitantes comparten la misma base.** Si alguien carga un archivo, lo ven todos.

## Para usarla con datos reales

Mientras no tenga usuarios y una base de datos externa, lo correcto es correrla en la
computadora de quien la usa:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Así los datos quedan en `data/costos.db`, en esa computadora y en ningún otro lado.
Conviene descargar el respaldo (pestaña *Cargar datos*) cada cierto tiempo.

El camino para tener una versión en línea con datos reales sería: una base PostgreSQL
externa (por ejemplo Supabase, que ya usaste en el Mogueómetro) más inicio de sesión.
Eso es un proyecto aparte.
