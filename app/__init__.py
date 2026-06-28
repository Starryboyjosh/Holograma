"""Capa web + orquestación del Holograma UNEV (refactor de Fase 3).

Esta es la **capa de servicios tipada** que el plan de mejora
(`ANALISIS_Y_PLAN_DE_MEJORA.md`, §5 y Fase 3) propone para reemplazar el
monkey-patching y el estado global de `main.py`/`call.py`. Envuelve los motores
buenos que ya existen (`llm_backend`, `vision/`, `stt/`, `hologram_controller`)
detrás de interfaces limpias. La Fase 3 (Pasos A–D) ya **cableó** estos servicios
en `main.py` por estrangulamiento (commits `2c2567b`/`97a885f`/`9fe1eb2`/`9b2afa0`),
validada contra un servidor real.

Servicios ya implementados, testeados (`tests/test_app_services.py`) y en uso por
`main.py`:

* `connection.ConnectionManager` — único emisor de eventos async hacia el cliente
  (reemplaza `send_to_web_client` + `run_coroutine_threadsafe`).
* `services.llm.LLMService` — envuelve la única ruta async `stream_llm_response`.
* `services.vision.CameraContextProvider` — sostiene el último análisis de cámara
  y construye su contexto (rompe el ciclo `call ↔ llm_backend`).
* `services.conversation.ConversationService` — orquesta prompt → LLM → eventos →
  TTS, con UN solo emisor y sin reemitir texto desde el TTS.

Pendiente (diferido a su propia sesión, ver `ANALISIS_Y_PLAN_DE_MEJORA.md` §8):
wrappers `tts`/`stt`/`hologram` y el movimiento de carpetas a `app/main.py` + `core/`.
"""
