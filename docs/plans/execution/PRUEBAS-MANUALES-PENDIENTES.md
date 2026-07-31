# Pruebas manuales pendientes

Verificaciones que **no** se pueden hacer desde la sesión de código y quedan a
cargo del humano. Se revisan todas juntas al terminar las WAVEs (decisión del
2026-07-30), no wave por wave.

Motivos típicos por los que una prueba cae acá:

* necesita **hardware físico** (altavoz, micrófono, ventiladores del holograma);
* necesita una **llamada de pago real** a un proveedor LLM (prohibido sin OK
  explícito);
* necesita **percepción humana** (¿suena bien?, ¿se ve bien?), no una aserción.

Estado: `[ ]` pendiente · `[x]` verificada · `[!]` falló → abrir hallazgo.

---

## WAVE-01 — Desbloquear el turno (commit `99d40c7`)

- [ ] **P01-1 · Fallback real con un proveedor caído.** Con `LLM_MODEL` apuntando
  a un modelo inexistente en OpenRouter, hacer una pregunta por voz y confirmar
  que el visitante **igual recibe respuesta** (cae a groq) en vez de silencio.
  *Cubierto por tests con dobles; falta la cadena real contra la red.*
- [ ] **P01-2 · `LLM_MAX_TOKENS=800` no trunca ni alarga de más.** Preguntar algo
  que dé respuesta larga ("¿qué carreras ofrece la universidad?") y confirmar
  que termina la frase en vez de cortarse a mitad. *Decisión D1, aplicada sólo
  en el `.env` local: falta decidir si sube a `.env.example`.*

## WAVE-02 — Filtro de razonamiento en streaming (commit `cd3b1cd`)

- [ ] **P02-1 · Smoke test de audio.** Con un modelo de razonamiento real
  (nemotron/qwen), preguntar por voz y **escuchar** que el holograma no lee su
  propio razonamiento y que la primera cláusula sigue saliendo rápido.
  *Requiere altavoz físico + llamada de pago: no verificable desde la sesión.*
- [ ] **P02-2 · Ruta web en el navegador.** Mismo turno desde el frontend:
  confirmar que los `text_chunk` que aparecen en pantalla no traen `<think>` ni
  variantes. *Los tests lo cubren con dobles; falta el WebSocket real.*
- [ ] **P02-3 · Rollback.** Arrancar con `HOLOGRAM_COT_FILTER=0` y confirmar que
  vuelve el comportamiento anterior (útil si el filtro come texto en producción).

## WAVE-03 — Instrumentación del turno (commit `9313531`)

- [ ] **P03-1 · Latencias reales.** Las dos columnas de tiempo de la línea base
  (`time_to_first_token_ms`, `time_to_first_clause_ms`) están **sin medir**: con
  backends dobles salen 0–1 ms, que no informa de nada. Hace falta un turno real
  contra OpenRouter/groq. Procedimiento: arrancar el kiosco con
  `python main.py 2> metrics.log`, hacer las 11 preguntas obligatorias por voz y
  guardar el `metrics.log`. Con eso quedan cerradas las dos columnas y además se
  confirma el peor caso de fallback (decisión **D4**) con números en vez de
  estimación. *Requiere llamada de pago real: prohibida sin OK explícito.*
- [ ] **P03-2 · La línea no ensucia el log del kiosco.** Arrancar sin redirigir y
  confirmar por vista que el log humano (CoT, TTS, cámara) sigue legible, y que
  `2> metrics.log` separa limpiamente los dos flujos. *Percepción humana.*
