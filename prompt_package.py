"""El **único** sitio donde se decide qué ve el modelo.

Antes de esta WAVE, cada ruta armaba su prompt por su cuenta: `call.ask_ai`
pedía `get_university_context()` y `stream_llm_response` volvía a pedirlo por
dentro, con su propio ``try/except ImportError``. Dos rutas, dos decisiones, y
ninguna forma de cambiar la política sin tocar las dos y esperar que no
divergieran. Acá se decide una vez y las dos rutas consumen el resultado.

Qué decide:

1. **Qué secciones institucionales entran**, preguntándole al router determinista
   de `skills.router` (sin red, sin embeddings).
2. **Cuánto puede ocupar** ese bloque, con tope por sección y tope total.
3. **Qué es intocable**: los guardarraíles (la nota UNEV≠UNED y la línea
   anti-invención) van siempre, aunque el presupuesto quede a cero.

Qué NO decide: el modelo, la temperatura, `max_tokens` (WAVE-09), la política de
cámara (WAVE-08) ni la memoria conversacional (WAVE-06). Y no importa `call`:
hacerlo reabriría el ciclo ``call ↔ llm_backend`` que el plan cerró.

Rollback::

    HOLOGRAM_SELECTIVE_CONTEXT=0

Con eso el paquete devuelve el bloque completo de `get_university_context()`,
exactamente el comportamiento anterior a esta WAVE, sin tocar código.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from security import clamp_text
from skills.router import MINIMUM_CONFIDENCE, RouteDecision, route_query
from skills.unev_content import MAX_FIELD_CHARS
from skills.university import get_context_sections, get_university_context
from utils import _env

__all__ = [
    "PromptPackage",
    "build_prompt_package",
    "build_university_context",
    "selective_context_enabled",
    "MAX_SECTION_CHARS",
    "MAX_CONTEXT_CHARS",
    # Reexportado para que quien lea el paquete sepa contra qué umbral se
    # decidió, sin tener que importar `skills.router` a mano.
    "MINIMUM_CONFIDENCE",
]

# --- Presupuesto -----------------------------------------------------------
# Tope **por sección**. Deliberadamente por debajo de los 8000 chars que
# `MAX_FIELD_CHARS` permite por campo en el panel: un solo campo inflado no debe
# poder llenar el prompt entero. Hoy la sección más grande es `honduras` (2.438
# chars), así que este tope no recorta nada real; existe para el día en que
# alguien pegue un PDF en un campo del editor.
MAX_SECTION_CHARS = 3000

# Tope **total** del bloque institucional. Con la selección típica el bloque
# ronda los 337–2.600 chars (tras la poda de WAVE A-1 la sección más grande,
# `honduras`, bajó a 2.290); el tope es el techo duro que impide volver a los
# 15.516 chars de la línea base por acumulación.
MAX_CONTEXT_CHARS = 4000

# Coherencia del presupuesto: si el tope por sección superase al total, el tope
# por sección no acotaría nada.
assert MAX_SECTION_CHARS <= MAX_CONTEXT_CHARS <= MAX_FIELD_CHARS


def selective_context_enabled() -> bool:
    """¿Enviar sólo las secciones que pide el router? Activo por defecto.

    ``HOLOGRAM_SELECTIVE_CONTEXT=0`` restituye el bloque completo. Mismo patrón
    (y misma lectura tolerante de valores) que ``metrics_enabled()``.
    """
    return _env("HOLOGRAM_SELECTIVE_CONTEXT", "1").lower() not in ("0", "false", "no", "off")


@dataclass(frozen=True)
class PromptPackage:
    """Todo lo que el modelo va a ver este turno, más lo que hay que medir.

    Es un contenedor de datos: no llama al LLM ni sabe de proveedores. Quien
    arma la lista final de mensajes sigue siendo `llm_backend._build_messages`,
    que recibe estas piezas ya decididas.
    """

    user_input: str
    system_prompt: str
    university_context: str
    camera_context: str | None = None
    # --- metadatos para la métrica de WAVE-03 ---
    sections: tuple[str, ...] = ()
    topic: str | None = None
    confidence: float = 0.0
    reason_code: str = "NO_LOCAL_MATCH"
    dropped_sections: tuple[str, ...] = field(default_factory=tuple)
    selective: bool = True

    @property
    def context_chars(self) -> int:
        """Lo mismo que anota `TurnMetrics.note_prompt` como ``context_chars``."""
        return len(self.university_context)

    @property
    def local_skill_hit(self) -> bool:
        """¿El router tenía una respuesta local para esta pregunta?

        Se deriva de la decisión ya tomada, sin volver a enrutar. Es el dato que
        `metrics._local_skill_would_answer` calcula por su cuenta cuando no hay
        paquete a mano.
        """
        return self.topic is not None

    def system_messages(self) -> list[dict[str, str]]:
        """Los mensajes de rol ``system``, en el orden en que van al modelo.

        Existe para que ningún llamador vuelva a escribir el formato del bloque
        de cámara; el orden y los prefijos son los de `_build_messages`.
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": self.university_context},
        ]
        if self.camera_context:
            messages.append(
                {"role": "system", "content": f"Contexto actual de la cámara:\n{self.camera_context}"}
            )
        return messages


def _guardrails_only() -> str:
    """El bloque con cero secciones: sólo cabecera y cierre.

    Es el suelo del presupuesto. Nunca se recorta por debajo de esto, ni aunque
    el tope total fuera menor: sin la nota UNEV≠UNED el STT vuelve a colar
    «UNED», y sin la línea de cierre el modelo rellena huecos inventando. Un
    prompt corto que alucina es peor que uno largo.
    """
    return get_context_sections(())


def _fit_budget(
    keys: tuple[str, ...],
    *,
    section_limit: int,
    total_limit: int,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """Ajusta la selección al presupuesto. Determinista y sin sorpresas.

    Dos recortes, los dos por **descarte de secciones completas**, nunca por
    corte a media frase:

    1. Una sección que ella sola supera ``section_limit`` se descarta. Truncar un
       dato institucional por la mitad es peor que omitirlo: media frase se lee
       como un hecho completo y equivocado, mientras que la ausencia la cubre el
       guardarraíl anti-invención.
    2. Si el conjunto supera ``total_limit``, se descarta **por la cola**. Las
       reglas del router listan sus secciones de más a menos relevante, así que
       la cola es siempre el acompañamiento, no la respuesta.

    Devuelve ``(texto, secciones_conservadas, secciones_descartadas)``.
    """
    floor = _guardrails_only()
    overhead = len(floor)

    kept: list[str] = []
    dropped: list[str] = []
    for key in keys:
        if len(get_context_sections((key,))) - overhead > section_limit:
            dropped.append(key)
            continue
        kept.append(key)

    while kept and len(get_context_sections(kept)) > total_limit:
        dropped.append(kept.pop())

    texto = get_context_sections(kept)
    if len(texto) > total_limit:
        # Sólo se llega acá si ni los guardarraíles caben en el presupuesto.
        # Se envían igual: son inviolables (ver `_guardrails_only`).
        texto, kept = floor, []
    # `clamp_text` es, además del truncador del proyecto, su saneador: quita los
    # caracteres de control invisibles con que se ofuscan inyecciones en los
    # campos del editor. Se aplica con el tamaño ya ajustado, así que acá sólo
    # sanea; el recorte real ya lo hicieron los dos descartes de arriba.
    return clamp_text(texto, len(texto)), tuple(kept), tuple(dropped)


def build_prompt_package(
    user_input: str,
    *,
    system_prompt: str | None = None,
    camera_context: str | None = None,
    event_mode: str | None = None,
    decision: RouteDecision | None = None,
    section_limit: int = MAX_SECTION_CHARS,
    total_limit: int = MAX_CONTEXT_CHARS,
    selective: bool | None = None,
) -> PromptPackage:
    """Arma el paquete de prompt del turno: sistema + contexto + cámara.

    ``system_prompt`` se resuelve solo si no se pasa, con el mismo
    `get_system_prompt(event_mode)` y el mismo blindaje que usaba
    `stream_llm_response` por dentro: si el import falla, el turno sigue con
    prompt vacío en vez de caerse.

    ``decision`` permite inyectar una decisión de router ya calculada (lo usan
    los tests); en producción se enruta acá.
    """
    if system_prompt is None:
        try:
            from skills.event_mode import get_system_prompt

            system_prompt = get_system_prompt(event_mode or "normal")
        except Exception:
            system_prompt = ""

    if decision is None:
        decision = route_query(user_input)

    use_selective = selective_context_enabled() if selective is None else selective
    if not use_selective:
        # Rollback exacto: el bloque completo, por la misma función y la misma
        # caché que antes de esta WAVE.
        return PromptPackage(
            user_input=user_input,
            system_prompt=system_prompt or "",
            university_context=get_university_context(),
            camera_context=camera_context,
            sections=tuple(),
            topic=decision.topic,
            confidence=decision.confidence,
            reason_code=decision.reason_code,
            selective=False,
        )

    context, kept, dropped = _fit_budget(
        decision.sections, section_limit=section_limit, total_limit=total_limit
    )
    return PromptPackage(
        user_input=user_input,
        system_prompt=system_prompt or "",
        university_context=context,
        camera_context=camera_context,
        sections=kept,
        topic=decision.topic,
        confidence=decision.confidence,
        reason_code=decision.reason_code,
        dropped_sections=dropped,
        selective=True,
    )


def build_university_context(
    user_input: str,
    *,
    event_mode: str | None = None,
) -> str:
    """Atajo: sólo el bloque institucional ya seleccionado y acotado.

    Es lo que necesitan los llamadores que ya tienen resuelto su propio
    ``system_prompt`` —`call.ask_ai` lo tiene— y sólo quieren reemplazar el
    ``get_university_context()` completo por la selección de esta WAVE.
    """
    return build_prompt_package(
        user_input, system_prompt="", event_mode=event_mode
    ).university_context
