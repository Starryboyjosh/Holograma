"""Tests del selector de secciones de contexto (WAVE-04).

Son los **primeros tests directos** sobre `skills/university.py`: hasta ahora el
bloque de contexto institucional —lo más pesado del prompt, 15.516 chars por
turno— no tenía ninguna red de seguridad.

El central es `test_todas_las_secciones_reproducen_el_bloque_actual`: WAVE-04 no
puede cambiar ni un carácter de lo que ve el LLM, porque el cambio de
comportamiento pertenece a WAVE-05 y hay que poder atribuirle cualquier
regresión.

Todos restauran las cachés al terminar (fixture `contexto_limpio`): son globales
de módulo y una prueba que las deje sucias contamina a las siguientes.
"""

import pytest

import skills.university as U
from skills.unev_content import TEXT_FIELDS


@pytest.fixture(autouse=True)
def contexto_limpio():
    """Cachés limpias antes y después de cada caso."""
    U.invalidate_context_cache()
    yield
    U.invalidate_context_cache()


def test_todas_las_secciones_reproducen_el_bloque_actual():
    """Paridad exacta: mismo texto, carácter por carácter."""
    completo = U.get_university_context()
    por_secciones = U.get_context_sections(U.context_section_keys())
    assert por_secciones == completo
    # La forma del bloque atómico: cabecera, campos, programas, cierre, Honduras.
    assert completo.startswith("Información institucional de UNEV")
    assert "no inventes" in completo


def test_subconjunto_contiene_solo_lo_pedido():
    info = U.get_unev_info()
    solo_direccion = U.get_context_sections(["address"])

    assert info["address"] in solo_direccion
    assert "Dirección / sede" in solo_direccion
    assert info["mission"] not in solo_direccion
    assert info["vision"] not in solo_direccion
    assert "- Programas (descripción completa de cada uno):" not in solo_direccion
    # Y pesa una fracción del bloque completo: es la premisa de WAVE-05.
    assert len(solo_direccion) < len(U.get_university_context()) // 10


def test_orden_de_lectura_estable():
    """El orden de salida es el de TEXT_FIELDS, no el de las claves de entrada."""
    claves = ["address", "mission", "name", "programs"]
    directo = U.get_context_sections(claves)
    invertido = U.get_context_sections(list(reversed(claves)))
    desordenado = U.get_context_sections(set(claves))

    assert directo == invertido == desordenado
    # `name` va antes que `mission`, y `mission` antes que `address`, como en
    # TEXT_FIELDS — aunque la entrada los pidiera al revés.
    assert (
        directo.index("Nombre corto / sigla")
        < directo.index("Misión")
        < directo.index("Dirección / sede")
    )


def test_campos_y_etiquetas_en_sincronia():
    """Guardarraíl permanente: 25 campos, 25 etiquetas, mismo orden.

    Sin esto, añadir un campo a `TEXT_FIELDS` y olvidar su etiqueta produce una
    línea `- clave_cruda: valor` en el prompt, silenciosamente.
    """
    assert list(TEXT_FIELDS) == list(U._CONTEXT_FIELD_LABELS)
    assert len(TEXT_FIELDS) == 25


def test_honduras_es_opcional():
    from skills.honduras import get_university_context as honduras_ctx

    marca = honduras_ctx()[:80]
    assert marca, "el contexto de Honduras no debería estar vacío en este repo"

    con = U.get_context_sections(["address", U.HONDURAS_SECTION])
    sin = U.get_context_sections(["address"])

    assert marca in con
    assert marca not in sin
    # Y sigue incluyéndose por defecto: nadie cambió los llamadores en WAVE-04.
    assert marca in U.get_university_context()


def test_invalidar_cache_limpia_todo(monkeypatch):
    """Con caché por sección, olvidar limpiarla es el fallo probable de WAVE-04."""
    original = U.get_unev_info()

    # Poblar las dos cachés: la del bloque completo y la de secciones sueltas.
    antes_completo = U.get_university_context()
    antes_parcial = U.get_context_sections(["address"])
    assert original["address"] in antes_parcial

    editado = dict(original)
    editado["address"] = "DIRECCIÓN EDITADA POR EL PANEL"
    monkeypatch.setattr(U, "get_unev_info", lambda: editado)

    # Sin invalidar, las cachés mandan: el cambio todavía no se ve.
    assert U.get_university_context() == antes_completo

    U.invalidate_context_cache()

    assert "DIRECCIÓN EDITADA POR EL PANEL" in U.get_context_sections(["address"])
    assert "DIRECCIÓN EDITADA POR EL PANEL" in U.get_university_context()
    assert original["address"] not in U.get_university_context()


def test_claves_desconocidas(capsys):
    """Se ignoran y se avisan una sola vez; nunca tumban el turno."""
    esperado = U.get_context_sections(["address"])
    con_basura = U.get_context_sections(["address", "no_existe", "otra_inventada"])
    assert con_basura == esperado

    err = capsys.readouterr().err
    assert "no_existe" in err
    assert "otra_inventada" in err

    # Segunda vez con la misma clave: sin aviso repetido (un router
    # desactualizado no puede inundar el log, un aviso por turno).
    U.get_context_sections(["address", "no_existe"])
    assert "no_existe" not in capsys.readouterr().err


def test_seccion_vacia_se_omite(monkeypatch):
    """Un campo vacío no produce una línea `- Etiqueta: ` colgada."""
    info = dict(U.get_unev_info())
    info["mission"] = "   "
    monkeypatch.setattr(U, "get_unev_info", lambda: info)
    U.invalidate_context_cache()

    salida = U.get_context_sections(["mission", "address"])

    assert "Misión" not in salida
    assert "Dirección / sede" in salida
