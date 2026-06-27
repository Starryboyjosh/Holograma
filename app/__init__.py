"""Capa web + orquestación del Holograma UNEV (refactor de Fase 3).

Esta es la **capa de servicios tipada** que el plan de mejora
(`ANALISIS_Y_PLAN_DE_MEJORA.md`, §5 y Fase 3) propone para reemplazar el
monkey-patching y el estado global de `main.py`/`call.py`. Es **aditiva**: envuelve
los motores buenos que ya existen (`llm_backend`, `vision/`, `stt/`,
`hologram_controller`) detrás de interfaces limpias, sin tocar todavía el arranque
en producción.

Estado actual (lo verificable sin levantar el backend ya está implementado y
testeado en `tests/test_app_services.py`):

* `connection.ConnectionManager` — único emisor de eventos async hacia el cliente
  (reemplaza `send_to_web_client` + `run_coroutine_threadsafe`).
* `services.llm.LLMService` — envuelve la única ruta async `stream_llm_response`.
* `services.vision.CameraContextProvider` — sostiene el último análisis de cámara
  y construye su contexto (rompe el ciclo `call ↔ llm_backend`).
* `services.conversation.ConversationService` — orquesta prompt → LLM → eventos →
  TTS, con UN solo emisor y sin reemitir texto desde el TTS.

Pendiente (necesita el backend/hardware real, ver HANDOFF.md §E):
wrappers `tts`/`stt`/`hologram`, y cablear estos servicios en `app/main.py`
borrando el monkey-patching del `lifespan` de `main.py`.
"""
