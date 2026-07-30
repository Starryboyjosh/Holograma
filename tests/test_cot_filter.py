"""WAVE-02 — el razonamiento del modelo no puede llegar al altavoz.

Hallazgo D: `_strip_qwen_thinking` sólo actúa sobre la respuesta completa, pero
la voz habla por cláusulas mientras el stream sigue abierto. Con un chunk como
``<think>El usuario pregunta…`` el TTS ya había hablado el razonamiento mucho
antes de que llegara el ``</think>`` que lo cerraba.

El filtro vive en el origen del stream (`llm_backend`), así que la ruta de voz y
la ruta web reciben tokens ya limpios sin duplicar lógica en cada consumidor.

Sin red y sin llamadas a APIs de pago: todo backend está monkeypatcheado.
"""

import asyncio
import sys
import types

from test_app_services import FakeLLM, RecordingConnection  # dobles ya existentes

import llm_backend as lb
from app.services.conversation import ConversationService

PROMPT = "¿cuánto dura Programación Web?"


def _filtrar(chunks, **kwargs):
    """Pasa una lista de trozos por un filtro y devuelve lo que sale, en orden."""
    f = lb._CotStreamFilter(**kwargs)
    salida = [f.feed(c) for c in chunks]
    salida.append(f.flush())
    return [s for s in salida if s]


# --------------------------------------------------------------------------- #
# El estado sobrevive al corte entre chunks
# --------------------------------------------------------------------------- #
def test_bloque_partido_entre_chunks_no_se_emite():
    """La etiqueta puede venir cortada por la mitad: el filtro no se despista."""
    chunks = ["<thi", "nk>razono", " mucho</thi", "nk>La respuesta."]

    assert "".join(_filtrar(chunks)) == "La respuesta."


def test_clausula_con_think_abierto_no_llega_al_tts():
    """El caso vivo del hallazgo D, chunk a chunk de un carácter (peor caso).

    `pop_ready_speech` corta por puntuación, así que sin filtro la primera
    cláusula hablada era "<think>El usuario pregunta por la duración." — el
    holograma leyendo su propio razonamiento en voz alta.
    """
    from utils import pop_ready_speech

    raw = (
        "<think>El usuario pregunta por la duración de Programación Web. "
        "Según el contexto son 2 años. Debo responder breve.</think>"
        "La carrera de Programación Web dura 2 años."
    )

    f = lb._CotStreamFilter()
    buf, first, hablado = "", True, []
    for ch in raw:  # el LLM puede emitir un token por carácter
        visible = f.feed(ch)
        if not visible:
            continue
        buf += visible
        ready, buf, first = pop_ready_speech(buf, first)
        hablado += ready
    buf += f.flush()
    ready, buf, first = pop_ready_speech(buf, first)
    hablado += ready
    if buf:
        hablado.append(buf)

    dicho = " ".join(hablado)
    assert "think" not in dicho.lower(), f"se habló razonamiento: {dicho!r}"
    assert "Debo responder breve" not in dicho
    assert "".join(hablado).replace(" ", "") == (
        "La carrera de Programación Web dura 2 años.".replace(" ", "")
    )


# --------------------------------------------------------------------------- #
# Lo que NO debe tocar
# --------------------------------------------------------------------------- #
def test_texto_sin_tags_pasa_intacto():
    """Identidad byte a byte: el filtro sólo puede quitar razonamiento.

    Es el criterio más importante de la WAVE: si el filtro recorta, come
    espacios o reordena, degrada todas las respuestas para arreglar unas pocas.
    """
    casos = [
        ["La matrícula cuesta 2,500 pesos."],
        ["La ", "matrícula ", "cuesta ", "2,500 ", "pesos."],
        list("Programación Web dura 2 años y medio, con 4 cuatrimestres."),
        ["Menos de 24 caracteres."],  # más corto que la cola retenida
        ["Un <b>tag</b> que no es de razonamiento <br> queda igual."],
        ["Comparación: 3 < 5 y 7 > 4."],  # signos sueltos, no etiquetas
        ["   espacios   al   borde   "],
        [""],
        ["línea 1\n\nlínea 2\ttabulada"],
    ]

    for chunks in casos:
        original = "".join(chunks)
        f = lb._CotStreamFilter()
        salida = "".join(f.feed(c) for c in chunks) + f.flush()
        assert salida == original, f"el filtro alteró {original!r} → {salida!r}"


# --------------------------------------------------------------------------- #
# Cobertura del juego de etiquetas
# --------------------------------------------------------------------------- #
def test_los_cinco_tags_se_filtran():
    """El filtro y `clean_for_tts` comparten las cinco etiquetas, no sólo <think>."""
    import call

    for tag in ("think", "thinking", "reasoning", "analysis", "scratchpad"):
        raw = f"<{tag}>ruido interno</{tag}>Respuesta visible."

        assert "".join(_filtrar([raw])) == "Respuesta visible."
        assert call.clean_for_tts(raw) == "Respuesta visible."
        # Mayúsculas y espacios sueltos dentro de la etiqueta.
        raro = f"< {tag.upper()} >ruido< / {tag} >Respuesta visible."
        assert "".join(_filtrar([raro])) == "Respuesta visible."
        assert call.clean_for_tts(raro) == "Respuesta visible."


def test_tag_abierto_sin_cerrar_al_final_se_descarta():
    """Sin ``</think>`` (el modelo agotó los tokens) no se habla nada de eso."""
    chunks = ["Voy a pensar. ", "<think>", "y me quedé sin tokens a mitad de"]

    assert "".join(_filtrar(chunks)) == "Voy a pensar. "


# --------------------------------------------------------------------------- #
# Independencia del log y rollback
# --------------------------------------------------------------------------- #
def test_filtro_funciona_con_LLM_LOG_COT_apagado(monkeypatch):
    """Filtrar y registrar son decisiones distintas.

    El kiosco corre con ``LLM_LOG_COT=0``; si el filtro dependiera de esa
    variable, justo en producción no filtraría nada.
    """
    monkeypatch.setenv("LLM_LOG_COT", "0")

    assert "".join(_filtrar(["<think>ruido</think>Respuesta."])) == "Respuesta."


def test_flag_desactiva_el_filtro(monkeypatch):
    """``HOLOGRAM_COT_FILTER=0`` devuelve el comportamiento anterior (rollback)."""
    monkeypatch.setenv("HOLOGRAM_COT_FILTER", "0")

    raw = "<think>ruido</think>Respuesta."
    assert "".join(_filtrar([raw])) == raw


# --------------------------------------------------------------------------- #
# La ruta web recibe lo mismo que la de voz
# --------------------------------------------------------------------------- #
def test_ruta_web_difunde_texto_limpio(monkeypatch):
    """El WebSocket no puede mostrar el razonamiento que la voz sí oculta.

    Filtrar en el origen (`_stream_backend_response`) es lo que mantiene las dos
    rutas alineadas: `ConversationService` no sabe nada de etiquetas.
    """
    fake_call = types.ModuleType("call")
    fake_call._last_camera_analysis = None
    fake_call._build_camera_context = lambda analysis: ""
    monkeypatch.setitem(sys.modules, "call", fake_call)

    monkeypatch.setattr(lb, "get_selected_backend", lambda: "openrouter")
    monkeypatch.setattr(lb, "_candidate_backends", lambda primary: ["openrouter"])

    async def fake_stream(backend, messages):
        # Ya filtrado en el origen: es lo que el consumidor debe ver.
        f = lb._CotStreamFilter()
        for trozo in ["<think>razono", " un poco</think>", "La carrera dura 2 años."]:
            visible = f.feed(trozo)
            if visible:
                yield visible
        resto = f.flush()
        if resto:
            yield resto

    monkeypatch.setattr(lb, "_stream_backend_response", fake_stream)

    async def run():
        emitidos = [c async for c in lb.stream_llm_response(PROMPT)]
        conn = RecordingConnection()
        servicio = ConversationService(llm=FakeLLM(emitidos), connection=conn)
        await servicio.handle_prompt(PROMPT)
        return conn

    conn = asyncio.run(run())

    texto = "".join(
        m["text"] for m in conn.messages if m.get("type") == "text_chunk"
    )
    assert texto == "La carrera dura 2 años."
    assert "think" not in texto.lower()
