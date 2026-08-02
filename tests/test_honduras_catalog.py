"""WAVE A-1 — el catálogo de cultura general vive fuera del import.

`honduras_cultura_general.json` (970 preguntas) ya no se carga al importar
`skills.honduras`: pesaba el arranque y ninguna regla del router lo consultaba.
Solo se lee bajo demanda con `get_cultura_general_info`.
"""

from skills.honduras import (
    HONDURAS_EXACT_LOOKUP,
    get_cultura_general_info,
    get_university_context,
)


def test_catalog_not_loaded_at_import():
    """El lookup del import solo tiene las claves de programs/próceres/etc."""
    assert len(HONDURAS_EXACT_LOOKUP) < 50
    assert "¿qué tipo de especie es abarema filamentosa?" not in HONDURAS_EXACT_LOOKUP


def test_catalog_lookup_exact_and_partial():
    assert (
        get_cultura_general_info("¿qué tipo de especie es abarema filamentosa?")
        .startswith("Especie de planta de la familia Fabaceae")
    )


def test_catalog_lookup_miss_returns_none():
    assert get_cultura_general_info("¿cuál es la capital de Alemania?") is None


def test_context_no_longer_counts_catalog_entries():
    ctx = get_university_context()
    assert "catálogo integrado de" not in ctx
    assert "Honduras" in ctx
