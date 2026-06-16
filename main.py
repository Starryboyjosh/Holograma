import os
import json
import asyncio
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from llm_backend import stream_llm_response

load_dotenv()

app = FastAPI(
    title="UNEV Hologram API",
    description="Unified async LLM streaming service and WebSocket chat server",
    version="1.0.0"
)

# Configurar middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Obtener contraseña del archivo .env o usar valor por defecto
CHAT_PASSWORD = os.getenv("CHAT_PASSWORD", "unev_admin_2026")

active_connections: List[WebSocket] = []
running_loop = None

def send_to_web_client(type_name: str, text: str, user_text: str = None):
    if not running_loop:
        return
    
    payload = {"type": type_name}
    if type_name == "status":
        payload["status"] = text
    elif type_name == "text_chunk":
        payload["text"] = text
    elif type_name == "text_done":
        payload["full_text"] = text
    elif type_name == "audio_status":
        payload["status"] = text
        payload["message"] = "Pipeline XTTS completado"
    elif type_name == "stt_transcript":
        payload["text"] = text
    elif type_name == "camera_event":
        payload["event"] = text
        
    if user_text:
        payload["user_text"] = user_text

    async def do_send():
        for ws in list(active_connections):
            try:
                await ws.send_json(payload)
            except Exception:
                if ws in active_connections:
                    active_connections.remove(ws)
                    
    asyncio.run_coroutine_threadsafe(do_send(), running_loop)

# --- Modelos Pydantic ---
class PasswordVerify(BaseModel):
    password: str

class ConfigUpdate(BaseModel):
    OLLAMA_MODEL: Optional[str] = None
    WHISPER_MODEL: Optional[str] = None
    HOLOGRAM_INPUT: Optional[str] = None
    HOLOGRAM_CAMERA: Optional[str] = None
    YOLO_MODEL: Optional[str] = None
    YOLO_INTERVAL_SECONDS: Optional[str] = None
    LLM_PROVIDER: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    PIPER_VOICE: Optional[str] = None
    HOLOGRAM_MODE: Optional[str] = None

class BoundingBoxModel(BaseModel):
    x: float
    y: float
    w: float
    h: float
    label: str
    desc: str

class TrainImagePayload(BaseModel):
    image: str
    boundingBoxes: List[BoundingBoxModel]

class VocabularyPayload(BaseModel):
    vocabulary: str

# --- Endpoints REST API ---

@app.post("/api/verify-password")
def verify_password(payload: PasswordVerify):
    if payload.password == CHAT_PASSWORD:
        return {"status": "ok"}
    return {"status": "error"}

@app.get("/api/config")
def get_config():
    config_path = "config.json"
    config_data = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception as e:
            print(f"Error reading config.json: {e}")
            
    return {
        "OLLAMA_MODEL": config_data.get("OLLAMA_MODEL", None),
        "WHISPER_MODEL": config_data.get("WHISPER_MODEL", "medium"),
        "HOLOGRAM_INPUT": config_data.get("HOLOGRAM_INPUT", "voice"),
        "HOLOGRAM_CAMERA": config_data.get("HOLOGRAM_CAMERA", "1"),
        "YOLO_MODEL": config_data.get("YOLO_MODEL", "yoloe26.pt"),
        "YOLO_INTERVAL_SECONDS": config_data.get("YOLO_INTERVAL_SECONDS", "1.0"),
        "LLM_PROVIDER": os.getenv("LLM_PROVIDER") or config_data.get("LLM_PROVIDER", "openrouter"),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY") or config_data.get("OPENROUTER_API_KEY", ""),
        "PIPER_VOICE": config_data.get("PIPER_VOICE", "es_MX-claude-high.onnx"),
        "HOLOGRAM_MODE": config_data.get("HOLOGRAM_MODE", "dark")
    }

@app.post("/api/config")
def update_config(payload: ConfigUpdate):
    config_path = "config.json"
    config_data = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception:
            pass
            
    if payload.OLLAMA_MODEL is not None:
        config_data["OLLAMA_MODEL"] = payload.OLLAMA_MODEL
        os.environ["OLLAMA_MODEL"] = str(payload.OLLAMA_MODEL) if payload.OLLAMA_MODEL else ""
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
    if payload.OPENROUTER_API_KEY is not None:
        config_data["OPENROUTER_API_KEY"] = payload.OPENROUTER_API_KEY
        os.environ["OPENROUTER_API_KEY"] = payload.OPENROUTER_API_KEY
    if payload.PIPER_VOICE is not None:
        config_data["PIPER_VOICE"] = payload.PIPER_VOICE
        os.environ["PIPER_VOICE"] = payload.PIPER_VOICE
    if payload.HOLOGRAM_MODE is not None:
        config_data["HOLOGRAM_MODE"] = payload.HOLOGRAM_MODE
        os.environ["HOLOGRAM_MODE"] = payload.HOLOGRAM_MODE
        
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
            
        # Also write to .env for persistence
        env_path = ".env"
        env_lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                env_lines = f.readlines()
        
        new_env_data = {}
        for line in env_lines:
            if "=" in line and not line.strip().startswith("#"):
                parts = line.split("=", 1)
                new_env_data[parts[0].strip()] = parts[1].strip()
        
        if payload.LLM_PROVIDER is not None:
            new_env_data["LLM_PROVIDER"] = payload.LLM_PROVIDER
        if payload.OPENROUTER_API_KEY is not None:
            new_env_data["OPENROUTER_API_KEY"] = payload.OPENROUTER_API_KEY
            
        with open(env_path, "w", encoding="utf-8") as f:
            for k, v in new_env_data.items():
                f.write(f"{k}={v}\n")
                
        return {"status": "ok", "config": config_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class SpeakPayload(BaseModel):
    text: str
    voice: Optional[str] = None

@app.get("/api/voices")
def get_voices():
    import glob
    from pathlib import Path
    onnx_files = glob.glob("es_*.onnx")
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
                voice_path = os.path.abspath(voice_path)
            os.environ["PIPER_MODEL_PATH"] = voice_path
        
        speak(payload.text, blocking=False)
        
        if payload.voice and old_voice is not None:
            os.environ["PIPER_MODEL_PATH"] = old_voice
        elif payload.voice:
            os.environ.pop("PIPER_MODEL_PATH", None)
            
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/train/image")
def train_image(payload: TrainImagePayload):
    print(f"[YOLO Training] Received training image with {len(payload.boundingBoxes)} bounding boxes.")
    try:
        os.makedirs("data", exist_ok=True)
        meta_path = "data/training_metadata.json"
        existing = []
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        
        for box in payload.boundingBoxes:
            existing.append({
                "label": box.label,
                "desc": box.desc,
                "x": box.x,
                "y": box.y,
                "w": box.w,
                "h": box.h,
                "timestamp": time.time()
            })
            
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=4)
            
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/train/vocabulary")
def train_vocabulary(payload: VocabularyPayload):
    print(f"[YOLO Training] Received open-vocabulary updates: {payload.vocabulary}")
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/open_vocabulary.txt", "w", encoding="utf-8") as f:
            f.write(payload.vocabulary)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- Rutas de Archivos Estáticos (Frontend) ---

@app.get("/")
def read_root():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return HTMLResponse(
        content="<h2>UNEV Hologram - Compilando frontend, por favor espera...</h2>", 
        status_code=200
    )

# Crear directorio de assets si no existe y montar de forma segura
os.makedirs("static/assets", exist_ok=True)
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

@app.get("/{path:path}")
def read_all_other_paths(path: str):
    # Si es una ruta de asset o estático directo
    static_file_path = os.path.join("static", path)
    if os.path.exists(static_file_path) and os.path.isfile(static_file_path):
        return FileResponse(static_file_path)
    
    # De lo contrario, fallback a index.html para SPA router
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return HTMLResponse(
        content="<h2>UNEV Hologram - Compilando frontend, por favor espera...</h2>", 
        status_code=200
    )


async def simulate_xtts_pipeline(text: str, websocket: WebSocket):
    """
    Simula el procesamiento del pipeline de audio (XTTS).
    Envía eventos de estado sobre la generación del audio.
    """
    await websocket.send_json({
        "type": "audio_status",
        "status": "processing",
        "message": "Iniciando pipeline de audio (XTTS)..."
    })
    
    # Simula la latencia de síntesis de voz
    await asyncio.sleep(0.8)
    
    # En un entorno con XTTS instalado y configurado, se invocaría el modelo de la siguiente forma:
    # wav_bytes = xtts_model.synthesize(text)
    # websocket.send_bytes(wav_bytes)
    
    await websocket.send_json({
        "type": "audio_status",
        "status": "completed",
        "message": f"Pipeline XTTS completado para el texto: '{text[:40]}...'"
    })

@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    print("[WebSocket] Cliente conectado al chat principal.")
    try:
        while True:
            # Espera mensaje del cliente
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                prompt = message_data.get("prompt", "")
            except ValueError:
                prompt = data
                
            if not prompt:
                continue

            print(f"[WebSocket] Prompt recibido: {prompt}")
            
            # Notifica que se inicia el streaming del LLM
            await websocket.send_json({"type": "status", "status": "streaming_started"})
            
            full_response = ""
            try:
                # Transmite los fragmentos de texto en tiempo real
                async for chunk in stream_llm_response(prompt):
                    full_response += chunk
                    await websocket.send_json({
                        "type": "text_chunk",
                        "text": chunk
                    })
                
                # Notifica que finalizó el streaming de texto
                await websocket.send_json({
                    "type": "text_done",
                    "full_text": full_response
                })
                print(f"[WebSocket] Stream finalizado. Respuesta completa: {full_response[:60]}...")
                
                # Reproducir voz en el host del holograma
                try:
                    from call import speak
                    speak(full_response, blocking=False)
                except Exception as e:
                    print(f"[WebSocket] Error reproduciendo voz en el host: {e}")
                
                # Pasa el texto final al pipeline de audio (XTTS)
                await simulate_xtts_pipeline(full_response, websocket)
                
            except Exception as e:
                print(f"[WebSocket] Error procesando la petición del LLM: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Error del backend de LLM: {str(e)}"
                })
                
    except WebSocketDisconnect:
        print("[WebSocket] Cliente desconectado.")
    except Exception as e:
        print(f"[WebSocket] Error inesperado en WebSocket: {e}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.on_event("startup")
async def startup_event():
    global running_loop
    running_loop = asyncio.get_running_loop()
    
    # Parchear/monkey-patch las funciones de call.py para que transmitan al frontend
    try:
        import call
        from stt.listener import WhisperListener
        
        # 1. Parchear speak
        original_speak = call.speak
        def custom_speak(text, blocking=True):
            send_to_web_client("status", "streaming_started")
            send_to_web_client("text_chunk", text)
            send_to_web_client("text_done", text)
            original_speak(text, blocking)
        call.speak = custom_speak
        
        # 2. Parchear listen_once para capturar transcripciones
        original_listen_once = WhisperListener.listen_once
        def custom_listen_once(self):
            user_input = original_listen_once(self)
            if user_input:
                send_to_web_client("stt_transcript", user_input)
            return user_input
        WhisperListener.listen_once = custom_listen_once
        
        # 3. Parchear callback de cámara
        original_callback = call._camera_detection_callback
        def custom_callback(event, count, analysis=None):
            send_to_web_client("camera_event", event)
            original_callback(event, count, analysis)
        call._camera_detection_callback = custom_callback
        
        print("[Startup] Monkey-patching de call.py y WhisperListener completado.")
    except Exception as e:
        print(f"[Startup] Error al aplicar monkey-patch de call.py: {e}")

    # Leer config.json
    config_path = "config.json"
    config_data = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception:
            pass
            
    use_voice = os.getenv("HOLOGRAM_INPUT", config_data.get("HOLOGRAM_INPUT", "")).lower() == "voice"
    use_camera = os.getenv("HOLOGRAM_CAMERA", config_data.get("HOLOGRAM_CAMERA", "")) == "1"

    if use_camera:
        try:
            from call import start_camera_thread
            start_camera_thread()
            print("[Startup] Hilo de cámara YOLO iniciado con éxito.")
        except Exception as e:
            print(f"[Startup] Error al iniciar hilo de cámara: {e}")
            
    if use_voice:
        try:
            from call import voice_loop
            import threading
            stt_thread = threading.Thread(target=voice_loop, daemon=True, name="stt-voice-loop")
            stt_thread.start()
            print("[Startup] Hilo de escucha de voz STT iniciado con éxito.")
        except Exception as e:
            print(f"[Startup] Error al iniciar hilo de voz STT: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
