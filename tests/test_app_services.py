"""Capa de servicios de Fase 3 (`app/`).

Blinda los contratos del refactor sin necesidad del backend real:

* `ConnectionManager` difunde a todas las conexiones y descarta las muertas.
* `LLMService` envuelve la ruta async e inyecta `camera_context`.
* `CameraContextProvider` construye contexto (rompe el ciclo `call ↔ llm_backend`).
* `ConversationService` emite la secuencia correcta por UN solo emisor, ejecuta el
  TTS fuera del loop y NO reemite texto (arreglo estructural del síntoma B).
"""

import asyncio
import sys
import threading
import time
import types

import llm_backend as lb
from app.connection import ConnectionManager
from app.services.conversation import ConversationService
from app.services.llm import LLMService
from app.services.vision import CameraContextProvider


# --------------------------------------------------------------------------- #
# Dobles de prueba
# --------------------------------------------------------------------------- #
class FakeWS:
    def __init__(self, fail: bool = False):
        self.sent: list[dict] = []
        self.fail = fail

    async def send_json(self, data: dict) -> None:
        if self.fail:
            raise RuntimeError("socket cerrado")
        self.sent.append(data)


class RecordingConnection:
    def __init__(self):
        self.messages: list[dict] = []

    async def broadcast(self, message: dict) -> None:
        self.messages.append(message)


class FakeLLM:
    def __init__(self, chunks, record: dict | None = None):
        self._chunks = chunks
        self._record = record

    async def stream(self, prompt: str, camera_context: str | None = None):
        if self._record is not None:
            self._record["prompt"] = prompt
            self._record["camera_context"] = camera_context
        for chunk in self._chunks:
            yield chunk


# --------------------------------------------------------------------------- #
# ConnectionManager
# --------------------------------------------------------------------------- #
def test_connection_manager_broadcasts_to_all():
    cm = ConnectionManager()
    a, b = FakeWS(), FakeWS()

    async def run():
        await cm.register(a)
        await cm.register(b)
        await cm.broadcast({"type": "ping"})

    asyncio.run(run())
    assert a.sent == [{"type": "ping"}]
    assert b.sent == [{"type": "ping"}]


def test_connection_manager_drops_dead_socket():
    cm = ConnectionManager()
    good, bad = FakeWS(), FakeWS(fail=True)

    async def run():
        await cm.register(good)
        await cm.register(bad)
        await cm.broadcast({"type": "x"})
        return cm.count

    remaining = asyncio.run(run())
    assert good.sent == [{"type": "x"}]
    assert remaining == 1  # el socket caído se purgó


def test_broadcast_threadsafe_bridges_thread_to_loop():
    """Puente hilo→loop: un hilo no-async difunde encolando en el loop ligado.

    Es exactamente lo que hacen los productores de voz/cámara tras retirar
    `send_to_web_client`; el manager es ahora dueño del salto con `bind_loop`.
    """
    cm = ConnectionManager()
    ws = FakeWS()
    loop = asyncio.new_event_loop()

    def run_loop():
        asyncio.set_event_loop(loop)
        loop.run_forever()

    worker = threading.Thread(target=run_loop, daemon=True)
    worker.start()
    try:
        # register() usa un asyncio.Lock, así que se ejecuta dentro del loop.
        asyncio.run_coroutine_threadsafe(cm.register(ws), loop).result(timeout=2)
        cm.bind_loop(loop)

        # Desde ESTE hilo (no-async), difundir vía el puente.
        cm.broadcast_threadsafe({"type": "camera_event", "event": "x", "count": 1})

        deadline = time.time() + 2
        while not ws.sent and time.time() < deadline:
            time.sleep(0.01)
    finally:
        loop.call_soon_threadsafe(loop.stop)
        worker.join(timeout=2)
        loop.close()

    assert ws.sent == [{"type": "camera_event", "event": "x", "count": 1}]


def test_broadcast_threadsafe_is_silent_without_bound_loop():
    """Sin loop ligado (arranque incompleto), no revienta el hilo; se descarta."""
    cm = ConnectionManager()
    cm.broadcast_threadsafe({"type": "x"})  # no debe lanzar


# --------------------------------------------------------------------------- #
# LLMService
# --------------------------------------------------------------------------- #
def test_llm_service_passes_camera_context_through():
    record: dict = {}
    service = LLMService(stream_fn=FakeLLM(["a", "b"], record=record).stream)

    async def collect():
        return [c async for c in service.stream("hola", camera_context="CTX")]

    assert asyncio.run(collect()) == ["a", "b"]
    assert record["camera_context"] == "CTX"
    assert record["prompt"] == "hola"


# --------------------------------------------------------------------------- #
# CameraContextProvider
# --------------------------------------------------------------------------- #
def test_camera_context_builds_with_injected_builder():
    provider = CameraContextProvider(builder=lambda a: f"CTX:{a['person_count']}")
    provider.update({"person_count": 3})
    assert provider.build_context() == "CTX:3"


def test_camera_context_is_none_without_analysis():
    provider = CameraContextProvider(builder=lambda a: "no debería llamarse")
    assert provider.build_context() is None


# --------------------------------------------------------------------------- #
# ConversationService — el corazón de la Fase 3
# --------------------------------------------------------------------------- #
def test_conversation_web_only_emits_text_exactly_once():
    conn = RecordingConnection()
    service = ConversationService(FakeLLM(["Hola ", "mundo"]), conn)

    full = asyncio.run(service.handle_prompt("hi"))

    assert full == "Hola mundo"
    assert [m["type"] for m in conn.messages] == [
        "status",
        "text_chunk",
        "text_chunk",
        "text_done",
    ]
    assert conn.messages[0]["status"] == "streaming_started"
    chunks = [m["text"] for m in conn.messages if m["type"] == "text_chunk"]
    assert chunks == ["Hola ", "mundo"]  # cada fragmento, una sola vez


def test_conversation_with_tts_emits_audio_progress_and_speaks_once():
    conn = RecordingConnection()
    spoken: list[str] = []
    service = ConversationService(
        FakeLLM(["Respuesta"]), conn, speak=lambda t: spoken.append(t)
    )

    full = asyncio.run(service.handle_prompt("hi"))

    assert full == "Respuesta"
    assert spoken == ["Respuesta"]  # TTS una vez, con el texto completo
    assert [m["type"] for m in conn.messages] == [
        "status",
        "text_chunk",
        "text_done",
        "audio_status",
        "audio_status",
    ]
    audio = [m["status"] for m in conn.messages if m["type"] == "audio_status"]
    assert audio == ["processing", "completed"]
    # El TTS NO reemite texto: hay exactamente un text_chunk (síntoma B).
    assert sum(1 for m in conn.messages if m["type"] == "text_chunk") == 1


def test_conversation_injects_camera_context_into_llm():
    record: dict = {}
    conn = RecordingConnection()
    camera = CameraContextProvider(builder=lambda a: f"CTX:{a['person_count']}")
    camera.update({"person_count": 2})
    service = ConversationService(FakeLLM(["x"], record=record), conn, camera=camera)

    asyncio.run(service.handle_prompt("hi"))
    assert record["camera_context"] == "CTX:2"


def test_conversation_emits_error_on_llm_failure():
    conn = RecordingConnection()

    class BoomLLM:
        async def stream(self, prompt, camera_context=None):
            raise RuntimeError("backend caído")
            yield ""  # inalcanzable: solo marca la función como async generator

    full = asyncio.run(ConversationService(BoomLLM(), conn).handle_prompt("hi"))

    assert full == ""
    assert conn.messages[0]["status"] == "streaming_started"
    assert conn.messages[-1]["type"] == "error"
    assert "backend caído" in conn.messages[-1]["message"]


# --------------------------------------------------------------------------- #
# Cycle break en stream_llm_response
# --------------------------------------------------------------------------- #
def test_stream_skips_call_import_when_context_injected(monkeypatch):
    """Con `camera_context` inyectado, NO se construye contexto desde `call`."""
    fake_call = types.ModuleType("call")
    fake_call._last_camera_analysis = {"person_count": 1}

    def boom(analysis):
        raise AssertionError("no debe tocar call cuando el contexto se inyecta")

    fake_call._build_camera_context = boom
    monkeypatch.setitem(sys.modules, "call", fake_call)
    monkeypatch.setattr(lb, "get_selected_backend", lambda: "local_only")
    monkeypatch.setattr(lb, "_candidate_backends", lambda primary: ["local_only"])
    monkeypatch.setattr(lb, "_local_only_reply", lambda prompt: "L")

    async def collect():
        return [c async for c in lb.stream_llm_response("hola", camera_context="CTX")]

    assert asyncio.run(collect()) == ["L"]
