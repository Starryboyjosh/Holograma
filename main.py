import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hologram_controller import HologramStateManager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.connection import ConnectionManager
from app.services.conversation import ConversationService
from app.services.llm import LLMService
from app.services.vision import CameraContextProvider
from auth_token import request_authorized
from llm_backend import list_ollama_models, probe_backend, stream_llm_response
from provider_config import all_providers_public_info
from security import (
    MAX_LABEL_CHARS,
    MAX_PROMPT_CHARS,
    MAX_TTS_CHARS,
    MAX_VOCAB_CHARS,
    clamp_text,
    redact_secrets,
)
from skills.unev_content import get_unev_info, save_unev_info
from utils import (
    _atomic_write_text,
    load_config,
    read_dotenv,
    write_dotenv,
)

# Regla de Oro A: rutas absolutas basadas en este archivo. Al ejecutarse como
# sidecar de Tauri el CWD puede ser arbitrario, así que anclamos CADA ruta a
# BASE_DIR en vez de mutar el CWD global del proceso con os.chdir() (efecto
# secundario a nivel de import que contaminaba a todo el proceso). config.json,
# .env, static/, data/ y los modelos se resuelven igual sin importar desde dónde
# se lance. Los módulos importados (call.py, vision/, stt/, skills/) ya anclan
# sus rutas a su propio __file__, así que tampoco dependen del CWD.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
INDEX_HTML = os.path.join(STATIC_DIR, "index.html")

load_dotenv(ENV_PATH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación (reemplaza @app.on_event, deprecado).

    Arranca: expone el event loop al hilo de TTS/cámara, parchea call.py para
    transmitir al frontend e inicia los hilos de cámara YOLO y voz STT.
    Apaga: cierra el controlador del holograma físico y limpia conexiones.
    """
    # El manager (dueño del registro de sockets) también es dueño del puente
    # hilo→loop: le entregamos el loop para que los hilos de voz/cámara difundan
    # con manager.broadcast_threadsafe. (Antes vivía como el global `running_loop`.)
    manager.bind_loop(asyncio.get_running_loop())

    # Parchear/monkey-patch las funciones de call.py para que transmitan al frontend
    try:
        import call
        from stt.listener import WhisperListener

        # El audio se procesa en el servidor: marcar modo web para que
        # voice_loop no lea stdin como push-to-talk (el botón llega por WS).
        call.WEB_MODE = True
        # Puente hilo de voz → WebSocket (estados listening / listen_idle / error).
        call._ws_emit = manager.broadcast_threadsafe

        # Antes aquí se parcheaba call.speak con un wrapper no-op para "no reemitir
        # texto desde el hilo de TTS". Ya es innecesario: el WS emite el texto vía
        # ConversationService y _host_speak usa call.speak SOLO para el audio; el
        # voice loop sigue llamando a call.speak directamente. Patch retirado.

        # 1. Parchear listen_once para capturar transcripciones. Corre en el hilo de
        # voz, así que difunde por el manager con el salto hilo→loop.
        original_listen_once = WhisperListener.listen_once

        def custom_listen_once(self):
            user_input = original_listen_once(self)
            if user_input:
                manager.broadcast_threadsafe(
                    {"type": "stt_transcript", "text": user_input}
                )
            return user_input

        WhisperListener.listen_once = custom_listen_once

        # 2. Parchear callback de cámara. Corre en el hilo de cámara: difunde por el
        # manager y alimenta el proveedor de visión.
        original_callback = call._camera_detection_callback

        def custom_callback(event, count, analysis=None):
            manager.broadcast_threadsafe(
                {"type": "camera_event", "event": event, "count": count}
            )
            # Alimenta el proveedor de visión: ConversationService lee
            # camera_provider.build_context() e inyecta camera_context en
            # stream_llm_response. llm_backend ya no importa call (sin fallback).
            camera_provider.update(analysis)
            original_callback(event, count, analysis)

        call._camera_detection_callback = custom_callback

        # En modo web call.main() no se ejecuta, por lo que el gestor físico debe
        # arrancarse explícitamente dentro del ciclo de vida de FastAPI.
        call.hologram.start()

        print("[Startup] Monkey-patching de call.py y WhisperListener completado.")
    except Exception as e:
        print(f"[Startup] Error al aplicar monkey-patch de call.py: {e}")

    # Leer config.json
    config_path = CONFIG_PATH
    config_data = load_config(config_path)

    use_voice = (
        os.getenv("HOLOGRAM_INPUT", config_data.get("HOLOGRAM_INPUT", "")).lower()
        == "voice"
    )
    use_camera = (
        os.getenv("HOLOGRAM_CAMERA", config_data.get("HOLOGRAM_CAMERA", "")) == "1"
    )

    if use_camera:
        try:
            from call import start_camera_thread

            start_camera_thread()
            print("[Startup] Hilo de cámara YOLO iniciado con éxito.")
        except Exception as e:
            print(f"[Startup] Error al iniciar hilo de cámara: {e}")

    if use_voice:
        try:
            import threading

            from call import voice_loop

            stt_thread = threading.Thread(
                target=voice_loop, daemon=True, name="stt-voice-loop"
            )
            stt_thread.start()
            print("[Startup] Hilo de escucha de voz STT iniciado con éxito.")
        except Exception as e:
            print(f"[Startup] Error al iniciar hilo de voz STT: {e}")

    yield

    # --- Apagado ordenado ---
    await manager.close_all()
    try:
        import call

        call.hologram.close()
    except Exception:
        pass
    print("[Shutdown] Aplicación detenida limpiamente.")


app = FastAPI(
    title="UNEV Hologram API",
    description="Unified async LLM streaming service and WebSocket chat server",
    version="1.0.0",
    lifespan=lifespan,
)

# Configurar middleware de CORS.
# El backend solo escucha en localhost. El WebView de Tauri hace peticiones
# cross-origin (p. ej. origen tauri://localhost o http://tauri.localhost) hacia
# 127.0.0.1:<puerto>. allow_origins=["*"] junto a allow_credentials=True es una
# combinación inválida que el navegador rechaza; como no usamos cookies/credenciales
# dejamos credentials en False.
#
# Por defecto se permite cualquier origen (comportamiento histórico, válido porque
# el servidor solo escucha en localhost). Para endurecerlo en producción tras
# validar el origen real del WebView, definir CORS_ALLOW_ORIGINS con una lista
# separada por comas, p. ej.:
#   CORS_ALLOW_ORIGINS=tauri://localhost,http://tauri.localhost,https://tauri.localhost
_cors_env = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
_cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Token de capacidad opcional para endpoints privilegiados (ajustes, contenido,
# cámara, entrenamiento). Apagado por defecto (HOLOGRAM_API_TOKEN vacío) para no
# romper la app actual; al activarlo, las escrituras exigen el header X-API-Token.
# Pendiente: la shell de Tauri debe entregar el token al frontend en cada llamada
# privilegiada (trabajo de seguridad diferido, junto al empaquetado del sidecar).
_API_TOKEN = os.getenv("HOLOGRAM_API_TOKEN", "").strip()


@app.middleware("http")
async def _api_token_gate(request, call_next):
    if _API_TOKEN and not request_authorized(
        request.url.path, request.method, request.headers.get("x-api-token"), _API_TOKEN
    ):
        return JSONResponse(
            {"status": "error", "message": "No autorizado: falta o no coincide X-API-Token."},
            status_code=401,
        )
    return await call_next(request)

# Registro único de conexiones WebSocket + difusión async (ver app/connection.py).
# Reemplaza la antigua lista global `active_connections` y centraliza el envío:
# tanto el endpoint async como los hilos de voz/cámara emiten por este manager.
manager = ConnectionManager()

# --- Capa de servicios de la Fase 3 (estado inyectado, sin globals mutables) ---
# Singletons a nivel de módulo. El proveedor de cámara DEBE ser único: el callback
# del hilo de cámara (provider.update) y el turno de conversación
# (provider.build_context) comparten el mismo análisis a través de esta instancia.
camera_provider = CameraContextProvider()


def _host_speak(text: str) -> None:
    """TTS en el host del holograma.

    Import perezoso de `call` (evita cargar la CLI al importar main) y usa el
    `call.speak` vigente. El ConversationService lo ejecuta con asyncio.to_thread,
    así que Piper (bloqueante) nunca corre sobre el event loop.
    """
    import call

    call.speak(text)


# Orquestador de un turno: emite por `manager`, inyecta contexto de cámara desde
# `camera_provider` y delega el TTS en `_host_speak`. Sin monkey-patching.
conversation = ConversationService(
    LLMService(stream_fn=stream_llm_response),
    connection=manager,
    camera=camera_provider,
    speak=_host_speak,
)


# --- Modelos Pydantic ---
class ConfigUpdate(BaseModel):
    OLLAMA_MODEL: str | None = None
    LLM_MODEL: str | None = None
    WHISPER_MODEL: str | None = None
    HOLOGRAM_INPUT: str | None = None
    HOLOGRAM_CAMERA: str | None = None
    YOLO_MODEL: str | None = None
    YOLO_INTERVAL_SECONDS: str | None = None
    LLM_PROVIDER: str | None = None
    OPENROUTER_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    NVIDIA_API_KEY: str | None = None
    # Endpoint propio compatible con OpenAI (vLLM, LM Studio, gateway…): el
    # proveedor "custom_openai" del contrato necesita key + URL base editables.
    OPENAI_COMPAT_API_KEY: str | None = None
    OPENAI_COMPAT_BASE_URL: str | None = None
    PIPER_VOICE: str | None = None
    HOLOGRAM_MODE: str | None = None
    GROQ_API_KEY: str | None = None
    HOLOGRAM_TCP_IP: str | None = None
    HOLOGRAM_TCP_PORT: int | None = None


class BoundingBoxModel(BaseModel):
    x: float
    y: float
    w: float
    h: float
    label: str
    desc: str


class TrainImagePayload(BaseModel):
    image: str
    boundingBoxes: list[BoundingBoxModel]


class VocabularyPayload(BaseModel):
    vocabulary: str


# --- Endpoints REST API ---


@app.get("/api/config")
def get_config():
    config_path = CONFIG_PATH
    config_data = load_config(config_path)

    openrouter_key = os.getenv("OPENROUTER_API_KEY") or config_data.get(
        "OPENROUTER_API_KEY", ""
    )
    openai_key = os.getenv("OPENAI_API_KEY") or config_data.get("OPENAI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config_data.get(
        "ANTHROPIC_API_KEY", ""
    )
    nvidia_key = os.getenv("NVIDIA_API_KEY") or config_data.get("NVIDIA_API_KEY", "")
    groq_key = os.getenv("GROQ_API_KEY") or config_data.get("GROQ_API_KEY", "")

    return {
        "OLLAMA_MODEL": config_data.get("OLLAMA_MODEL", None),
        "WHISPER_MODEL": config_data.get("WHISPER_MODEL", "medium"),
        "HOLOGRAM_INPUT": config_data.get("HOLOGRAM_INPUT", "voice"),
        "HOLOGRAM_CAMERA": config_data.get("HOLOGRAM_CAMERA", "1"),
        "YOLO_MODEL": config_data.get("YOLO_MODEL", "yoloe-26n-seg.pt"),
        "YOLO_INTERVAL_SECONDS": config_data.get("YOLO_INTERVAL_SECONDS", "1.0"),
        "LLM_PROVIDER": os.getenv("LLM_PROVIDER")
        or config_data.get("LLM_PROVIDER", "openrouter"),
        "LLM_MODEL": os.getenv("LLM_MODEL")
        or config_data.get("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct"),
        "OPENROUTER_API_KEY": "",
        "OPENAI_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "NVIDIA_API_KEY": "",
        "GROQ_API_KEY": "",
        "OPENROUTER_API_KEY_SET": bool(openrouter_key),
        "OPENAI_API_KEY_SET": bool(openai_key),
        "ANTHROPIC_API_KEY_SET": bool(anthropic_key),
        "NVIDIA_API_KEY_SET": bool(nvidia_key),
        "GROQ_API_KEY_SET": bool(groq_key),
        # URL base del endpoint propio compatible con OpenAI (no es secreto): se
        # devuelve para que el formulario la pueda pre-rellenar. La key nunca.
        "OPENAI_COMPAT_BASE_URL": os.getenv("OPENAI_COMPAT_BASE_URL")
        or config_data.get("OPENAI_COMPAT_BASE_URL", ""),
        "PIPER_VOICE": config_data.get("PIPER_VOICE", "es_MX-claude-high.onnx"),
        "HOLOGRAM_MODE": config_data.get("HOLOGRAM_MODE", "dark"),
        "HOLOGRAM_TCP_IP": os.getenv("HOLOGRAM_TCP_IP")
        or config_data.get("HOLOGRAM_TCP_IP", ""),
        "HOLOGRAM_TCP_PORT": os.getenv("HOLOGRAM_TCP_PORT")
        or config_data.get("HOLOGRAM_TCP_PORT", "50200"),
    }


@app.post("/api/config")
def update_config(payload: ConfigUpdate):
    config_path = CONFIG_PATH
    config_data = load_config(config_path)

    if payload.OLLAMA_MODEL is not None:
        val = payload.OLLAMA_MODEL if payload.OLLAMA_MODEL is not None else ""
        config_data["OLLAMA_MODEL"] = val
        os.environ["OLLAMA_MODEL"] = str(val)
    if payload.WHISPER_MODEL is not None:
        config_data["WHISPER_MODEL"] = payload.WHISPER_MODEL
        os.environ["WHISPER_MODEL"] = payload.WHISPER_MODEL
    if payload.HOLOGRAM_INPUT is not None:
        config_data["HOLOGRAM_INPUT"] = payload.HOLOGRAM_INPUT
        os.environ["HOLOGRAM_INPUT"] = payload.HOLOGRAM_INPUT
    if payload.HOLOGRAM_CAMERA is not None:
        config_data["HOLOGRAM_CAMERA"] = payload.HOLOGRAM_CAMERA
        os.environ["HOLOGRAM_CAMERA"] = payload.HOLOGRAM_CAMERA
    if payload.YOLO_MODEL is not None:
        config_data["YOLO_MODEL"] = payload.YOLO_MODEL
        os.environ["YOLO_MODEL"] = payload.YOLO_MODEL
    if payload.YOLO_INTERVAL_SECONDS is not None:
        config_data["YOLO_INTERVAL_SECONDS"] = payload.YOLO_INTERVAL_SECONDS
        os.environ["YOLO_INTERVAL_SECONDS"] = payload.YOLO_INTERVAL_SECONDS
    if payload.LLM_PROVIDER is not None:
        config_data["LLM_PROVIDER"] = payload.LLM_PROVIDER
        os.environ["LLM_PROVIDER"] = payload.LLM_PROVIDER
    if payload.LLM_MODEL is not None:
        config_data["LLM_MODEL"] = payload.LLM_MODEL
        os.environ["LLM_MODEL"] = payload.LLM_MODEL
    if payload.OPENROUTER_API_KEY is not None:
        config_data["OPENROUTER_API_KEY"] = payload.OPENROUTER_API_KEY
        os.environ["OPENROUTER_API_KEY"] = payload.OPENROUTER_API_KEY
    if payload.OPENAI_API_KEY is not None:
        config_data["OPENAI_API_KEY"] = payload.OPENAI_API_KEY
        os.environ["OPENAI_API_KEY"] = payload.OPENAI_API_KEY
    if payload.ANTHROPIC_API_KEY is not None:
        config_data["ANTHROPIC_API_KEY"] = payload.ANTHROPIC_API_KEY
        os.environ["ANTHROPIC_API_KEY"] = payload.ANTHROPIC_API_KEY
    if payload.NVIDIA_API_KEY is not None:
        config_data["NVIDIA_API_KEY"] = payload.NVIDIA_API_KEY
        os.environ["NVIDIA_API_KEY"] = payload.NVIDIA_API_KEY
    if payload.GROQ_API_KEY is not None:
        config_data["GROQ_API_KEY"] = payload.GROQ_API_KEY
        os.environ["GROQ_API_KEY"] = payload.GROQ_API_KEY
    if payload.OPENAI_COMPAT_API_KEY is not None:
        config_data["OPENAI_COMPAT_API_KEY"] = payload.OPENAI_COMPAT_API_KEY
        os.environ["OPENAI_COMPAT_API_KEY"] = payload.OPENAI_COMPAT_API_KEY
    if payload.OPENAI_COMPAT_BASE_URL is not None:
        config_data["OPENAI_COMPAT_BASE_URL"] = payload.OPENAI_COMPAT_BASE_URL
        os.environ["OPENAI_COMPAT_BASE_URL"] = payload.OPENAI_COMPAT_BASE_URL
    if payload.PIPER_VOICE is not None:
        config_data["PIPER_VOICE"] = payload.PIPER_VOICE
        os.environ["PIPER_VOICE"] = payload.PIPER_VOICE
    if payload.HOLOGRAM_MODE is not None:
        config_data["HOLOGRAM_MODE"] = payload.HOLOGRAM_MODE
        os.environ["HOLOGRAM_MODE"] = payload.HOLOGRAM_MODE
    if payload.HOLOGRAM_TCP_IP is not None:
        config_data["HOLOGRAM_TCP_IP"] = payload.HOLOGRAM_TCP_IP.strip()
        os.environ["HOLOGRAM_TCP_IP"] = payload.HOLOGRAM_TCP_IP.strip()
    if payload.HOLOGRAM_TCP_PORT is not None:
        config_data["HOLOGRAM_TCP_PORT"] = str(payload.HOLOGRAM_TCP_PORT)
        os.environ["HOLOGRAM_TCP_PORT"] = str(payload.HOLOGRAM_TCP_PORT)

    # Agrega parámetros por defecto si faltan en config_data
    default_config = {
        "OLLAMA_MODEL": "",
        "WHISPER_MODEL": "small",
        "HOLOGRAM_INPUT": "voice",
        "HOLOGRAM_CAMERA": "1",
        "YOLO_MODEL": "yoloe-26n-seg.pt",
        "YOLO_INTERVAL_SECONDS": "0.6",
        "LLM_PROVIDER": "openrouter",
        "LLM_MODEL": "meta-llama/llama-3.3-70b-instruct",
        "OPENROUTER_API_KEY": "",
        "OPENAI_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "NVIDIA_API_KEY": "",
        "GROQ_API_KEY": "",
        "PIPER_VOICE": "es_MX-claude-high.onnx",
        "HOLOGRAM_MODE": "dark",
        "HOLOGRAM_TCP_IP": "",
        "HOLOGRAM_TCP_PORT": "50200",
    }
    for k, v in default_config.items():
        if k not in config_data:
            config_data[k] = v

    try:
        _atomic_write_text(config_path, json.dumps(config_data, indent=4))

        # Also write to .env for persistence
        env_path = ENV_PATH
        new_env_data = read_dotenv(env_path)

        if payload.LLM_PROVIDER is not None:
            new_env_data["LLM_PROVIDER"] = payload.LLM_PROVIDER
        if payload.LLM_MODEL is not None:
            new_env_data["LLM_MODEL"] = payload.LLM_MODEL
        if payload.OPENROUTER_API_KEY is not None:
            new_env_data["OPENROUTER_API_KEY"] = payload.OPENROUTER_API_KEY
        if payload.OPENAI_API_KEY is not None:
            new_env_data["OPENAI_API_KEY"] = payload.OPENAI_API_KEY
        if payload.ANTHROPIC_API_KEY is not None:
            new_env_data["ANTHROPIC_API_KEY"] = payload.ANTHROPIC_API_KEY
        if payload.NVIDIA_API_KEY is not None:
            new_env_data["NVIDIA_API_KEY"] = payload.NVIDIA_API_KEY
        if payload.GROQ_API_KEY is not None:
            new_env_data["GROQ_API_KEY"] = payload.GROQ_API_KEY
        if payload.OPENAI_COMPAT_API_KEY is not None:
            new_env_data["OPENAI_COMPAT_API_KEY"] = payload.OPENAI_COMPAT_API_KEY
        if payload.OPENAI_COMPAT_BASE_URL is not None:
            new_env_data["OPENAI_COMPAT_BASE_URL"] = payload.OPENAI_COMPAT_BASE_URL
        if payload.HOLOGRAM_TCP_IP is not None:
            new_env_data["HOLOGRAM_TCP_IP"] = payload.HOLOGRAM_TCP_IP.strip()
        if payload.HOLOGRAM_TCP_PORT is not None:
            new_env_data["HOLOGRAM_TCP_PORT"] = str(payload.HOLOGRAM_TCP_PORT)

        write_dotenv(env_path, new_env_data)

        # Aplicar el destino físico en caliente; no hace falta reiniciar FastAPI.
        if payload.HOLOGRAM_TCP_IP is not None or payload.HOLOGRAM_TCP_PORT is not None:
            manager = _get_holo_manager()
            ip = str(config_data.get("HOLOGRAM_TCP_IP", "")).strip()
            port = int(config_data.get("HOLOGRAM_TCP_PORT", "50200"))
            if ip:
                manager.configure(ip, port)
            else:
                manager.disable()

        # No devolver secretos al navegador: redacta las API keys de la respuesta.
        safe_config = {
            k: ("***" if k.endswith("_API_KEY") and v else v)
            for k, v in config_data.items()
        }
        return {"status": "ok", "config": safe_config}
    except Exception as e:
        # No filtrar una API key si apareciera en el mensaje de la excepción.
        return {"status": "error", "message": redact_secrets(e, os.environ)}


class LlmTestPayload(BaseModel):
    provider: str
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None


@app.get("/api/providers")
def get_providers():
    """Lista de proveedores de IA con metadata segura (sin secretos).

    La interfaz la usa para pintar el selector con descripciones amistosas, el
    estado 'configurado/no configurado' de cada key y si admite descubrimiento de
    modelos o requiere URL base.
    """
    return {"providers": all_providers_public_info(os.environ)}


@app.get("/api/ollama/models")
def get_ollama_models():
    """Modelos instalados en el Ollama local (equivalente a ``ollama list``).

    La pantalla de Ajustes lo usa para rellenar el desplegable de modelo cuando
    el proveedor es Ollama. No requiere token (solo lectura, como /api/providers).
    """
    result = list_ollama_models()
    return {
        "status": "ok" if result["ok"] else "error",
        "models": result["models"],
        "message": result["message"],
    }


@app.post("/api/llm/test")
def test_llm(payload: LlmTestPayload):
    """Prueba real de proveedor/modelo/key/URL sin guardar nada.

    Devuelve un mensaje accionable ('API key inválida', 'modelo no existe',
    'no se pudo conectar', …). Nunca persiste ni devuelve la key enviada.
    """
    result = probe_backend(
        payload.provider,
        api_key=(payload.api_key or None),
        model=(payload.model or None),
        base_url=(payload.base_url or None),
    )
    return {"status": "ok" if result["ok"] else "error", "message": result["message"]}


@app.get("/api/unev-content")
def get_unev_content():
    """Contenido institucional de UNEV (fuente única editable)."""
    return {"status": "ok", "content": get_unev_info()}


@app.post("/api/unev-content")
def update_unev_content(payload: dict):
    """Valida y guarda el contenido de UNEV; recarga la fuente en caliente.

    Devuelve un mensaje accionable si el contenido es inválido. Es la única
    forma autorizada de editar la información institucional desde la interfaz.
    """
    try:
        merged = save_unev_info(payload)
        return {"status": "ok", "content": merged}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": redact_secrets(e, os.environ)}


class CameraToggle(BaseModel):
    enabled: bool


@app.post("/api/camera")
def set_camera(payload: CameraToggle):
    """Enciende o apaga la cámara.

    Por defecto, *apagar en la UI* **no** detiene el hilo YOLO: el holograma
    sigue viendo (uniforme, presencia) para el LLM; solo deja de servir el feed
    MJPEG cuando no hay suscriptores. Para liberar el dispositivo de verdad
    (LED apagado, otra app puede usar la cámara) define
    ``HOLOGRAM_CAMERA_RELEASE_ON_UI_OFF=1``.
    """
    try:
        if payload.enabled:
            from call import start_camera_thread

            start_camera_thread()
        else:
            release = os.getenv("HOLOGRAM_CAMERA_RELEASE_ON_UI_OFF", "0").lower() in (
                "1",
                "true",
                "yes",
            )
            if release:
                from call import stop_camera_thread

                stop_camera_thread()
            else:
                print(
                    "[Cámara] UI ocultó/apagó el visor; detección YOLO sigue "
                    "activa para el LLM (HOLOGRAM_CAMERA_RELEASE_ON_UI_OFF=0)."
                )
        return {"status": "ok", "enabled": payload.enabled}
    except Exception as e:
        return {"status": "error", "message": redact_secrets(e, os.environ)}


class SpeakPayload(BaseModel):
    text: str
    voice: str | None = None


@app.get("/api/voices")
def get_voices():
    import glob
    from pathlib import Path

    onnx_files = glob.glob(os.path.join(MODELS_DIR, "es_*.onnx"))
    voices = [Path(f).name for f in onnx_files]
    if not voices:
        voices = ["es_MX-claude-high.onnx"]
    return {"voices": voices}


@app.post("/api/speak")
def play_speak(payload: SpeakPayload):
    try:
        from call import speak

        old_voice = os.environ.get("PIPER_MODEL_PATH")
        if payload.voice:
            voice_path = payload.voice
            if not os.path.isabs(voice_path):
                # Antes os.path.abspath() resolvía contra el CWD (que os.chdir
                # forzaba a BASE_DIR); ahora anclamos explícitamente a BASE_DIR.
                voice_path = os.path.join(BASE_DIR, voice_path)
            os.environ["PIPER_MODEL_PATH"] = voice_path

        speak(clamp_text(payload.text, MAX_TTS_CHARS), blocking=False)

        if payload.voice and old_voice is not None:
            os.environ["PIPER_MODEL_PATH"] = old_voice
        elif payload.voice:
            os.environ.pop("PIPER_MODEL_PATH", None)

        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": redact_secrets(e, os.environ)}


@app.post("/api/train/image")
def train_image(payload: TrainImagePayload):
    print(
        f"[YOLO Training] Received training image with {len(payload.boundingBoxes)} bounding boxes."
    )
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(os.path.join(DATA_DIR, "images"), exist_ok=True)
        meta_path = os.path.join(DATA_DIR, "training_metadata.json")
        existing = []
        if os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as f:
                existing = json.load(f)

        # Save image
        image_data = payload.image
        import base64

        image_filename = f"image_{int(time.time())}.jpg"
        image_path = os.path.join(DATA_DIR, "images", image_filename)

        if image_data and "base64," in image_data:
            header, encoded = image_data.split("base64,", 1)
            with open(image_path, "wb") as f:
                f.write(base64.b64decode(encoded))

        thumbnail_url = f"/data/images/{image_filename}" if image_data else ""

        for box in payload.boundingBoxes:
            new_id = int(time.time() * 1000)
            existing.append(
                {
                    "id": new_id,
                    # Acotar etiqueta/descr.: son editables y terminan en el prompt
                    # del LLM, así que se limita la superficie de inyección/abuso.
                    "label": clamp_text(box.label, MAX_LABEL_CHARS),
                    "desc": clamp_text(box.desc, MAX_LABEL_CHARS),
                    "x": box.x,
                    "y": box.y,
                    "w": box.w,
                    "h": box.h,
                    "thumbnail": thumbnail_url,
                    "timestamp": time.time(),
                }
            )

        _atomic_write_text(meta_path, json.dumps(existing, indent=4))

        return {"status": "ok", "items": existing}
    except Exception as e:
        return {"status": "error", "message": redact_secrets(e, os.environ)}


@app.get("/api/train/metadata")
def get_training_metadata():
    meta_path = os.path.join(DATA_DIR, "training_metadata.json")
    items = load_config(meta_path)
    if not isinstance(items, list):
        items = []
    return {"status": "ok", "items": items}


@app.post("/api/train/vocabulary")
def train_vocabulary(payload: VocabularyPayload):
    vocabulary = clamp_text(payload.vocabulary, MAX_VOCAB_CHARS)
    print(f"[YOLO Training] Received open-vocabulary updates ({len(vocabulary)} chars).")
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        _atomic_write_text(os.path.join(DATA_DIR, "open_vocabulary.txt"), vocabulary)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": redact_secrets(e, os.environ)}


class HologramConnect(BaseModel):
    ip: str
    port: int | None = 50200


class HologramCommand(BaseModel):
    command: str
    index: int | None = None


# --- Conexión del holograma y compatibilidad de comandos TCP ---


def _get_holo_manager() -> "HologramStateManager":
    import call

    return call.hologram


@app.post("/api/hologram/connect")
def holo_connect(payload: HologramConnect):
    try:
        manager = _get_holo_manager()
        manager.configure(payload.ip, payload.port or 50200)
        # La conexión física ocurre en el worker fail-soft; la interfaz consulta
        # el estado periódicamente mientras continúan los reintentos.
        return {
            "status": "ok",
            "connected": manager.is_connected,
            "ip": manager.ip,
            "port": manager.port,
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "ip": payload.ip}


@app.post("/api/hologram/disconnect")
def holo_disconnect():
    try:
        _get_holo_manager().disable()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/hologram/command")
def holo_command(payload: HologramCommand):
    try:
        cmd = payload.command.lower()
        _get_holo_manager().execute(cmd, payload.index)
        return {"status": "ok", "command": cmd, "index": payload.index}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/hologram/status")
def holo_status():
    import call

    manager = call.hologram
    return {
        "connected": manager.is_connected,
        "ip": manager.ip or "",
        "port": manager.port,
        "ai_paused": getattr(call, "_hologram_paused", False),
    }


@app.post("/api/hologram/pause_ai")
def pause_ai():
    try:
        import call

        call.pause_hologram()
        return {"status": "ok", "ai_paused": True}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/hologram/resume_ai")
def resume_ai():
    try:
        import call

        call.resume_hologram()
        return {"status": "ok", "ai_paused": False}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- Transmisión de video YOLO en vivo (MJPEG) ---


def _placeholder_jpeg(message: str = "Esperando camara..."):
    """Build a simple 'no signal' JPEG so the <img> always shows something."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    frame[:] = (25, 18, 11)  # tono oscuro acorde a la interfaz
    cv2.putText(
        frame, message, (60, 190),
        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (29, 92, 226), 2, cv2.LINE_AA,
    )
    ok, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes() if ok else None


@app.get("/api/video_feed")
async def video_feed():
    """Transmite los cuadros YOLO anotados como MJPEG (async: no bloquea el loop).

    Antes era un endpoint síncrono cuyo generador usaba time.sleep: cada cliente
    del feed ocupaba un worker del threadpool y el sleep bloqueaba ese hilo. Ahora
    es async con asyncio.sleep, así que el stream cede el control al event loop
    entre cuadros y convive con el WebSocket y el resto de endpoints sin pelear por
    los hilos del pool.
    """
    import call

    async def generate():
        placeholder = _placeholder_jpeg()
        # Suscribirse activa la codificación JPEG en el hilo de cámara; al cerrarse
        # el generador (cliente desconecta) se da de baja y el detector deja de
        # codificar si no queda nadie mirando.
        call.camera_feed_subscribe()
        try:
            while True:
                jpeg = call.get_latest_camera_jpeg()
                if jpeg is None:
                    jpeg = placeholder
                    if jpeg is None:
                        await asyncio.sleep(0.2)
                        continue
                    await asyncio.sleep(0.2)
                else:
                    await asyncio.sleep(0.04)  # ~25 fps
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                )
        finally:
            call.camera_feed_unsubscribe()

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# --- Rutas de Archivos Estáticos (Frontend) ---


@app.get("/")
def read_root():
    if os.path.exists(INDEX_HTML):
        return FileResponse(INDEX_HTML)
    return HTMLResponse(
        content="<h2>UNEV Hologram - Compilando frontend, por favor espera...</h2>",
        status_code=200,
    )


# Crear directorio de assets si no existe y montar de forma segura
os.makedirs(os.path.join(STATIC_DIR, "assets"), exist_ok=True)
app.mount(
    "/assets",
    StaticFiles(directory=os.path.join(STATIC_DIR, "assets")),
    name="assets",
)

os.makedirs(DATA_DIR, exist_ok=True)
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")


@app.get("/{path:path}")
def read_all_other_paths(path: str):
    # Si es una ruta de asset o estático directo
    static_file_path = os.path.join(STATIC_DIR, path)
    if os.path.exists(static_file_path) and os.path.isfile(static_file_path):
        return FileResponse(static_file_path)

    # De lo contrario, fallback a index.html para SPA router
    if os.path.exists(INDEX_HTML):
        return FileResponse(INDEX_HTML)
    return HTMLResponse(
        content="<h2>UNEV Hologram - Compilando frontend, por favor espera...</h2>",
        status_code=200,
    )


@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    await manager.register(websocket)
    print("[WebSocket] Cliente conectado al chat principal.")
    try:
        # Informar al cliente del modo de voz actual (ptt / presentation / auto).
        try:
            from call import get_trigger_mode

            await websocket.send_json(
                {"type": "voice_mode", "mode": get_trigger_mode()}
            )
        except Exception:
            pass

        while True:
            # Espera mensaje del cliente
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
            except ValueError:
                message_data = {"prompt": data}

            # Cambiar el modo de activación de voz en caliente desde la WebApp.
            if message_data.get("type") == "set_mode":
                try:
                    from call import set_trigger_mode

                    new_mode = set_trigger_mode(message_data.get("mode", ""))
                    await manager.broadcast({"type": "voice_mode", "mode": new_mode})
                except Exception as e:
                    print(f"[WebSocket] No se pudo cambiar el modo: {e}")
                continue

            # Push-to-talk desde la WebApp: dispara la escucha del micrófono del
            # servidor (Whisper). El hilo voice_loop transcribe y responde.
            if message_data.get("type") == "listen":
                try:
                    from call import request_listen

                    request_listen()
                    await websocket.send_json(
                        {"type": "status", "status": "listening"}
                    )
                except Exception as e:
                    print(f"[WebSocket] No se pudo solicitar escucha: {e}")
                continue

            # El prompt llega de un visitante: acotar tamaño y quitar caracteres
            # de control antes de mandarlo al LLM (evita abuso de coste / DoS).
            prompt = clamp_text(message_data.get("prompt", ""), MAX_PROMPT_CHARS)
            if not prompt:
                continue

            print(f"[WebSocket] Prompt recibido ({len(prompt)} chars).")

            # Un turno completo lo orquesta ConversationService: emite por el
            # ConnectionManager la secuencia streaming_started → text_chunk* →
            # text_done → audio_status(processing/completed), inyecta el contexto de
            # cámara y corre el TTS (bloqueante) fuera del event loop con to_thread.
            # Difunde a TODOS los clientes conectados (igual que el voice loop), no
            # solo a este socket: todas las vistas del mismo holograma ven el turno.
            await conversation.handle_prompt(prompt)

    except WebSocketDisconnect:
        print("[WebSocket] Cliente desconectado.")
    except Exception as e:
        print(f"[WebSocket] Error inesperado en WebSocket: {e}")
    finally:
        await manager.unregister(websocket)




if __name__ == "__main__":
    import argparse

    import uvicorn

    # Puerto/host configurables para poder arrancar como sidecar de Tauri, que
    # elige un puerto libre y lo pasa por --port (o variable HOLOGRAM_PORT).
    # reload va apagado por defecto: el modo recarga lanza un subproceso que el
    # shell de Tauri no podría cerrar limpiamente. Para desarrollo web normal
    # se puede pasar --reload.
    parser = argparse.ArgumentParser(description="UNEV Hologram API server")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("HOLOGRAM_PORT", "8000")),
        help="Puerto TCP donde sirve FastAPI (default 8000 / $HOLOGRAM_PORT)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("HOLOGRAM_HOST", "127.0.0.1"),
        help="Host de escucha (default 127.0.0.1)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Activa autorecarga de uvicorn (solo desarrollo web)",
    )
    args = parser.parse_args()

    uvicorn.run("main:app", host=args.host, port=args.port, reload=args.reload)
