"""Pruebas de la interfaz: corren streamlit_app.py sin navegador (AppTest).

No revisan cómo se ve, sino que ninguna pestaña se caiga y que los botones
principales hagan lo que dicen.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from costos import db

APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")


@pytest.fixture
def app(tmp_path, monkeypatch):
    # Cada prueba usa su propia base temporal: nunca toca data/costos.db.
    monkeypatch.setattr(db, "RUTA_DB", tmp_path / "prueba.db")
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception, at.exception
    return at


def _metrica(at, etiqueta):
    return next(m.value for m in at.metric if m.label == etiqueta)


def test_arranca_con_los_datos_de_ejemplo(app):
    assert _metrica(app, "Presupuesto total") == "₡675,000,000"
    assert _metrica(app, "Obras en rojo") == "1 de 4"


def test_cambiar_de_obra_no_rompe_nada(app):
    opciones = app.selectbox[0].options
    for opcion in opciones:
        # Después de cada run() los elementos se vuelven a crear: hay que buscarlos de nuevo.
        app.selectbox[0].set_value(opcion).run()
        assert not app.exception, opcion
        assert app.selectbox[0].value == opcion


def test_la_tolerancia_cambia_el_semaforo(app):
    app.slider[0].set_value(0).run()           # sin tolerancia, todo lo que se pasa es rojo
    assert _metrica(app, "Obras en rojo") == "3 de 4"


def test_registrar_un_gasto(app):
    app.number_input[0].set_value(1_000_000)
    app.text_input[0].set_value("Proveedor de prueba")
    boton = next(b for b in app.button if b.label == "Guardar gasto")
    boton.click().run()
    assert not app.exception
    assert _metrica(app, "Gastado") == "₡226,813,300"     # 225 813 300 + 1 000 000


def test_un_gasto_de_cero_muestra_error(app):
    boton = next(b for b in app.button if b.label == "Guardar gasto")
    boton.click().run()
    assert any("mayor que cero" in e.value for e in app.error)
    assert _metrica(app, "Gastado") == "₡225,813,300"     # no cambió
