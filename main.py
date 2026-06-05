import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
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

@app.get("/")
def read_root():
    return {
        "status": "online",
        "provider": os.getenv("LLM_PROVIDER", "openrouter"),
        "model": os.getenv("LLM_MODEL")
    }

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
