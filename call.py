"""
UNEV Hologram — Main entry point.

Regla de Oro A: Todas las rutas usan pathlib.Path.
Regla de Oro B: Micrófono con sounddevice (no pyaudio).
Regla de Oro C: Dependencias centralizadas en requirements.txt.

Usage:
    python call.py              # Modo teclado (default)
    python call.py --voice      # Modo voz (micrófono → Whisper → LLM → Piper)
    python call.py --camera     # Detección de personas con YOLO
    python call.py --voice --camera  # Voz + cámara
"""

import base64
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

from hologram_controller import create_hologram_manager
from llm_backend import generate_reply, get_backend_status, get_selected_backend
from skills.appearance import get_cordial_observation
from skills.event_mode import get_greeting, get_system_prompt
from skills.presence import PresenceManager
from skills.router import route_local_skill
from skills.university import get_university_context, normalize_text
from utils import configure_utf8_stdio

configure_utf8_stdio()

# Fix for Wayland/CachyOS.
os.environ["QT_QPA_PLATFORM"] = "xcb"

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Cargar configuración unificada desde config.json (Regla A: Path)
CONFIG_FILE = BASE_DIR / "config.json"
if CONFIG_FILE.exists():
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            config_data = json.load(f)
            for key, val in config_data.items():
                if val is not None:
                    os.environ[key] = str(val)
    except Exception as e:
        print(f"AVISO: No se pudo cargar {CONFIG_FILE.name}: {e}")

CURRENT_MODE = os.getenv("HOLOGRAM_MODE", "normal")
DEFAULT_PIPER_MODEL = "es_MX-claude-high.onnx"
presence_manager = PresenceManager(
    greeting_cooldown_seconds=120, absence_reset_seconds=20
)
speak_lock = threading.Lock()
ai_busy = False

# Puente con el ventilador holográfico físico (TCP). Deshabilitado (no-op) si
# HOLOGRAM_TCP_IP no está definida — la IA corre igual sin dispositivo conectado.
hologram = create_hologram_manager()


# ======================================================================
# TTS helpers
# ======================================================================


def clean_for_tts(text):
    """Remove characters that can sound awkward when read by a TTS engine."""
    replacements = {
        "*": "",
        "[": "",
        "]": "",
        "`": "",
        "#": "",
        "_": "",
    }

    clean_text = re.sub(
        r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE
    )
    clean_text = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", clean_text)
    clean_text = re.sub(r"https?://\S+|www\.\S+", "", clean_text)
    clean_text = re.sub(r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF]", "", clean_text)
    for old, new in replacements.items():
        clean_text = clean_text.replace(old, new)

    clean_text = re.sub(r"\s+", " ", clean_text)
    return clean_text.strip()


def get_piper_command_args():
    """Return the command used to run Piper if it is available."""
    configured_command = os.getenv("PIPER_COMMAND")
    if configured_command:
        return configured_command.split()

    # ponytail: piper/ dir contains piper/piper/ subdir with binary
    bundled_piper_dir = BASE_DIR / "piper" / "piper"
    bundled_piper = bundled_piper_dir / "piper"
    bundled_espeak_data = bundled_piper_dir / "espeak-ng-data"
    if bundled_piper.exists():
        args = [str(bundled_piper)]
        if bundled_espeak_data.exists():
            args.extend(["--espeak_data", str(bundled_espeak_data)])
        return args

    for command in ["piper", "piper.exe"]:
        executable = shutil.which(command)
        if executable:
            return [executable]

    for venv_name in [".venv", ".env", "venv"]:
        venv_dir = BASE_DIR / venv_name

        posix_piper = venv_dir / "bin" / "piper"
        if posix_piper.exists():
            for python_name in ["python", "python3"]:
                venv_python = venv_dir / "bin" / python_name
                if venv_python.exists():
                    return [str(venv_python), str(posix_piper)]
            return [str(posix_piper)]

        windows_piper = venv_dir / "Scripts" / "piper.exe"
        if windows_piper.exists():
            return [str(windows_piper)]

    piper_spec = importlib.util.find_spec("piper")
    if piper_spec is not None and piper_spec.origin:
        spec_path = Path(piper_spec.origin).resolve()
        local_linux_bundle = (BASE_DIR / "piper").resolve()
        if local_linux_bundle not in spec_path.parents:
            return [sys.executable, "-m", "piper"]

    return None


def get_piper_install_hint():
    """Return a short installation hint for the current platform."""
    if platform.system() == "Windows":
        return (
            "Instala Piper en el entorno del proyecto con: "
            "py -m venv .venv && .\\.venv\\Scripts\\python -m pip install piper-tts"
        )

    return (
        "Instala Piper en el entorno del proyecto con: "
        "python -m venv .venv && ./.venv/bin/python -m pip install piper-tts"
    )


def get_piper_model_path():
    """Return the Piper voice model to use, preferring Spanish voices."""
    voice_env = os.getenv("PIPER_VOICE")
    if voice_env:
        voice_path = Path(voice_env)
        if not voice_path.is_absolute():
            voice_path = BASE_DIR / voice_path
        if voice_path.exists():
            return str(voice_path)

    configured_model = os.getenv("PIPER_MODEL_PATH")
    if configured_model:
        return str(Path(configured_model).expanduser())

    default_model = BASE_DIR / "models" / DEFAULT_PIPER_MODEL
    if default_model.exists():
        return str(default_model)

    spanish_models = sorted((BASE_DIR / "models").glob("es_*.onnx"))
    if spanish_models:
        return str(spanish_models[0])

    return str(default_model)


def get_piper_sample_rate(model_path):
    """Read Piper sample rate from the model JSON sidecar when available."""
    config_path = Path(f"{model_path}.json")  # Regla A

    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        return "22050"
    except json.JSONDecodeError:
        print(f"AVISO: No pude leer {config_path}. Usando 22050 Hz.")
        return "22050"

    sample_rate = config.get("audio", {}).get("sample_rate", 22050)
    return str(sample_rate)


def is_wsl():
    """Return True when running inside Windows Subsystem for Linux."""
    return (
        bool(os.getenv("WSL_DISTRO_NAME")) or "microsoft" in platform.release().lower()
    )


def get_powershell_command():
    """Return a PowerShell executable path on Windows or WSL if available."""
    for command in ["powershell.exe", "powershell", "pwsh.exe", "pwsh"]:
        powershell = shutil.which(command)
        if powershell:
            return powershell

    wsl_powershell = Path(
        "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    )
    if wsl_powershell.exists():
        return str(wsl_powershell)

    return None


def run_powershell(script):
    """Run a PowerShell script and return True when it succeeds."""
    powershell = get_powershell_command()
    if not powershell:
        print("AVISO: No encontré PowerShell para reproducir voz en Windows.")
        return False

    try:
        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
        )
    except Exception as error:
        print(f"Error ejecutando PowerShell: {error}")
        return False

    if result.stdout.strip():
        print(result.stdout.strip())

    if result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.strip())
        return False

    return True


def play_wav_with_windows(wav_path):
    """Play a WAV file with Windows' built-in SoundPlayer."""
    encoded_path = base64.b64encode(
        str(Path(wav_path).resolve()).encode("utf-8")
    ).decode("ascii")
    script = (
        f"$path = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_path}')); "
        "$player = New-Object System.Media.SoundPlayer; "
        "$player.SoundLocation = $path; "
        "$player.Load(); "
        "$player.PlaySync(); "
        "$player.Dispose();"
    )
    return run_powershell(script)


def play_wav_file(wav_path):
    """Play a WAV file on Windows, Linux, or macOS using available system tools."""
    system_name = platform.system()

    if system_name == "Windows":
        return play_wav_with_windows(wav_path)

    if system_name == "Darwin":
        players = [["afplay", wav_path]]
    else:
        players = [
            ["aplay", wav_path],
            ["paplay", wav_path],
            ["pw-play", wav_path],
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", wav_path],
            ["mpv", "--no-video", "--really-quiet", wav_path],
        ]

    for player_command in players:
        if not shutil.which(player_command[0]):
            continue

        try:
            result = subprocess.run(
                player_command,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                text=True,
            )
        except Exception as error:
            print(f"AVISO: No pude usar {player_command[0]} para audio: {error}")
            continue

        if result.returncode == 0:
            return True

        if result.stderr.strip():
            print(f"AVISO: {player_command[0]} falló: {result.stderr.strip()}")

    print(
        "AVISO: No encontré reproductor de audio compatible. "
        "En Linux instala aplay, paplay, pw-play, ffplay o mpv."
    )
    return False


def speak_with_piper(text):
    """Use Piper TTS and play the generated WAV file on the current OS."""
    piper_command_args = get_piper_command_args()
    if not piper_command_args:
        print("AVISO: No encontré Piper. Intentaré usar una voz nativa del sistema.")
        print(get_piper_install_hint())
        return False

    model_path = get_piper_model_path()

    # Regla A: pathlib for path checks
    if not Path(model_path).exists():
        print(
            f"ERROR: No encontré la voz {model_path}. "
            "Descarga una voz de Piper en español o define PIPER_MODEL_PATH."
        )
        return False

    config_path = Path(f"{model_path}.json")
    if not config_path.exists():
        print(
            f"ERROR: Falta {config_path}. "
            "Piper necesita el archivo .onnx y su .onnx.json correspondiente."
        )
        return False

    temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav_path = Path(temp_wav.name)  # Regla A
    temp_wav.close()

    try:
        timeout_seconds = int(os.getenv("PIPER_TIMEOUT_SECONDS", "120"))
    except ValueError:
        timeout_seconds = 120

    try:
        subprocess_env = os.environ.copy()
        bundled_lib_dir = BASE_DIR / "piper"
        if (bundled_lib_dir / "libpiper_phonemize.so").exists():
            current_ld_path = subprocess_env.get("LD_LIBRARY_PATH", "")
            paths = [str(bundled_lib_dir)]
            if current_ld_path:
                paths.append(current_ld_path)
            subprocess_env["LD_LIBRARY_PATH"] = os.pathsep.join(paths)

        result = subprocess.run(
            [
                *piper_command_args,
                "--model",
                model_path,
                "--output_file",
                str(wav_path),
            ],
            input=f"{text}\n",
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=timeout_seconds,
            env=subprocess_env,
        )

        if result.returncode != 0:
            print("AVISO: Piper no pudo generar la voz.")
            if result.stderr.strip():
                print(result.stderr.strip())
            return False

        return play_wav_file(str(wav_path))
    except subprocess.TimeoutExpired:
        print("AVISO: Piper tardó demasiado generando la voz.")
        return False
    except Exception as error:
        print(f"Error reproduciendo voz con Piper: {error}")
        return False
    finally:
        try:
            wav_path.unlink()  # Regla A
        except OSError:
            pass


def speak_with_windows_voice(text):
    """Use Windows built-in speech synthesis when Piper is unavailable."""
    encoded_text = base64.b64encode(text.encode("utf-8")).decode("ascii")
    preferred_voice = os.getenv("WINDOWS_TTS_VOICE", "")
    encoded_voice = base64.b64encode(preferred_voice.encode("utf-8")).decode("ascii")
    script = (
        f"$text = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_text}')); "
        f"$preferredVoice = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_voice}')); "
        "Add-Type -AssemblyName System.Speech; "
        "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "if (![string]::IsNullOrWhiteSpace($preferredVoice)) { "
        'try { $speaker.SelectVoice($preferredVoice) } catch { Write-Output "AVISO: No encontré la voz indicada en WINDOWS_TTS_VOICE." } '
        "} else { "
        "$voices = @($speaker.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'es-*' }); "
        "if ($voices.Count -gt 0) { $speaker.SelectVoice($voices[0].VoiceInfo.Name) } "
        'else { Write-Output "AVISO: Windows no tiene una voz en español instalada; usando la voz predeterminada." } '
        "}; "
        "$speaker.Volume = 100; "
        "$speaker.Rate = 0; "
        "$speaker.Speak($text); "
        "$speaker.Dispose();"
    )
    return run_powershell(script)


def speak_with_linux_tts(text):
    """Use lightweight Linux TTS fallbacks when Piper is unavailable."""
    for command in ["espeak-ng", "espeak"]:
        executable = shutil.which(command)
        if not executable:
            continue

        for voice in ["es-419", "es-la", "es"]:
            try:
                result = subprocess.run(
                    [executable, "-v", voice, text],
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                    text=True,
                    timeout=60,
                )
            except Exception as error:
                print(f"AVISO: No pude usar {command}: {error}")
                break

            if result.returncode == 0:
                return True

    spd_say = shutil.which("spd-say")
    if spd_say:
        try:
            result = subprocess.run(
                [spd_say, "-l", "es", text],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                text=True,
                timeout=60,
            )
            return result.returncode == 0
        except Exception as error:
            print(f"AVISO: No pude usar spd-say: {error}")

    return False


import queue

# Configuración del pipeline de streaming TTS
_MIN_FIRST_CHUNK_LEN = 23  # Latencia baja inicial (ej. "Hola, buenas tardes.")
_MIN_SENTENCE_LEN = 30  # Oración promedio
_CLAUSE_RE = re.compile(r"(?<=[.!?;:—])\s+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _split_into_chunks(text):
    """
    Divide el texto en fragmentos listos para TTS.
    El primero usa cláusulas para salir rápido; el resto oraciones completas.
    """
    chunks = []
    buf = ""
    first_chunk_sent = False

    # Limpieza previa de bloques problemáticos
    text = clean_for_tts(text)
    if not text:
        return []

    # Procesamos el texto de forma secuencial simulando la llegada de tokens
    words = text.split(" ")
    for i, word in enumerate(words):
        buf += word + " "
        sep = _SENTENCE_RE if first_chunk_sent else _CLAUSE_RE
        min_len = _MIN_SENTENCE_LEN if first_chunk_sent else _MIN_FIRST_CHUNK_LEN

        # Buscar límites
        matches = list(sep.finditer(buf))
        if matches:
            last_match = matches[-1]
            head = buf[: last_match.end()].strip()
            if len(head) >= min_len:
                chunks.append(head)
                buf = buf[last_match.end() :]
                first_chunk_sent = True

    # El sobrante final
    remainder = buf.strip()
    if remainder:
        chunks.append(remainder)

    return chunks


def speak_worker(q):
    """Worker de hilo que consume y habla los fragmentos secuencialmente."""
    while True:
        chunk = q.get()
        if chunk is None:
            q.task_done()
            break

        tts_backend = os.getenv("TTS_BACKEND", "auto").lower().strip()
        system_name = platform.system()

        try:
            print(f"\nSpeaking chunk: {chunk}")
            if tts_backend in ["auto", "piper"]:
                if speak_with_piper(chunk):
                    continue
                if tts_backend == "piper":
                    continue

            if system_name == "Windows" and tts_backend in [
                "auto",
                "windows",
                "native",
            ]:
                if speak_with_windows_voice(chunk):
                    continue

            if is_wsl() and tts_backend in ["auto", "windows", "native"]:
                if speak_with_windows_voice(chunk):
                    continue

            if system_name == "Linux" and tts_backend in [
                "auto",
                "linux",
                "native",
                "espeak",
            ]:
                if speak_with_linux_tts(chunk):
                    continue

            print(f"AVISO: No pude reproducir voz para el fragmento: {chunk}")
        except Exception as e:
            print(f"Error en el reproductor de voz: {e}")
        finally:
            q.task_done()


def speak(text, blocking=True):
    """Speak text using Piper when possible, with OS-native fallbacks.
    Utiliza segmentación inteligente por cláusulas y oraciones para streaming de audio.
    """
    chunks = _split_into_chunks(text)
    if not chunks:
        return

    # Evitar reproducción superpuesta usando el speak_lock
    acquired = speak_lock.acquire(blocking=blocking)
    if not acquired:
        print(f"[TTS] Omitiendo habla para evitar traslape: {text[:60]}...")
        return

    # El holograma muestra la animación de "hablando" mientras dura el TTS.
    hologram.set_state("speaking")

    try:
        q = queue.Queue()
        for chunk in chunks:
            q.put(chunk)
        q.put(None)  # Sentinel de finalización

        if blocking:
            # Iniciar hilo de reproducción y esperar a que termine
            worker_thread = threading.Thread(
                target=speak_worker, args=(q,), daemon=True
            )
            worker_thread.start()
            q.join()
            speak_lock.release()
            hologram.set_state("idle")
        else:
            # En modo no-bloqueante, el worker libera el lock al terminar
            def _non_blocking_worker(q, lock):
                try:
                    speak_worker(q)
                    q.join()
                finally:
                    lock.release()
                    hologram.set_state("idle")

            worker_thread = threading.Thread(
                target=_non_blocking_worker, args=(q, speak_lock), daemon=True
            )
            worker_thread.start()
            # NO liberar el lock aquí — el worker lo hará al terminar
            return
    except Exception:
        speak_lock.release()
        raise


# ======================================================================
# AI / LLM helpers
# ======================================================================


def ask_ai(user_input, mode=None):
    mode = mode or CURRENT_MODE

    if get_selected_backend() == "local_only":
        local_response = route_local_skill(user_input)
        if local_response:
            return local_response

    return generate_reply(
        user_input=user_input,
        system_prompt=get_system_prompt(mode),
        university_context=get_university_context(),
    )


# ======================================================================
# Command / mode handling
# ======================================================================


def set_mode(user_input):
    global CURRENT_MODE

    text = normalize_text(user_input)

    if text in ["modo jueces", "jueces", "modo juez"]:
        CURRENT_MODE = "judges"
        return "Modo jueces activado."

    if text in ["modo expo", "expo", "modo exposicion", "exposicion"]:
        CURRENT_MODE = "expo"
        return "Modo exposición activado."

    if text in ["modo admisiones", "admisiones", "admision"]:
        CURRENT_MODE = "admissions"
        return "Modo admisiones activado."

    if text in ["modo normal", "normal"]:
        CURRENT_MODE = "normal"
        return "Modo normal activado."

    return None


def get_help_text():
    return (
        "Comandos disponibles: saludar, persona, grupo, formal, se fue, backend, "
        "modo jueces, modo expo, modo admisiones, modo normal, ayuda y salir. "
        "También puedes preguntarme por carreras, admisiones, ubicación o información oficial de UNEV."
    )


def handle_command(user_input):
    text = normalize_text(user_input)

    if text in ["ayuda", "help", "comandos"]:
        return get_help_text()

    if text == "backend":
        return get_backend_status()

    mode_response = set_mode(user_input)
    if mode_response:
        return mode_response

    if text in ["saludar", "hola holograma"]:
        return get_greeting(CURRENT_MODE)

    if text in ["persona", "detectar persona", "alguien llego"]:
        if presence_manager.should_greet(True):
            return get_greeting(CURRENT_MODE)

        return "Ya detecté al visitante. Me mantendré atento sin repetir el saludo demasiado seguido."

    if text in ["grupo", "detectar grupo"]:
        if presence_manager.should_greet_group():
            return get_cordial_observation("grupo")
        return "Ya me presenté a un grupo recientemente."

    if text in ["formal", "vestimenta formal", "elegante"]:
        presence_manager.should_greet(True)
        return get_cordial_observation("formal")

    if text in ["juez visual", "jueces visual", "evaluadores"]:
        presence_manager.should_greet(True)
        return get_cordial_observation("jueces")

    if text in ["se fue", "persona se fue", "nadie"]:
        presence_manager.force_person_left()
        return "Entendido. Vuelvo a modo espera."

    return None


# ======================================================================
# YOLO camera detection (background thread)
# ======================================================================


def _camera_detection_callback(event, count, analysis=None):
    """Handle YOLO detection events from the background camera thread."""
    global ai_busy
    analysis = analysis or {}
    if ai_busy or speak_lock.locked():
        if event == "person_left":
            presence_manager.force_person_left()
            hologram.set_state("idle")
            print("[Cámara] La persona se fue. Vuelvo a modo espera (sin interrumpir).")
        return

    if event == "person_entered":
        if presence_manager.should_greet(True):
            face_description = analysis.get("face_description")
            greeting = get_greeting(CURRENT_MODE)
            if face_description:
                greeting = f"{face_description} {greeting}"
            speak(greeting, blocking=False)

    elif event == "group_detected":
        if presence_manager.should_greet_group():
            face_description = analysis.get("face_description")
            observation = get_cordial_observation("grupo")
            if face_description:
                observation = f"{face_description} {observation}"
            speak(observation, blocking=False)

    elif event == "person_left":
        presence_manager.force_person_left()
        hologram.set_state("idle")
        print("[Cámara] La persona se fue. Vuelvo a modo espera.")


def start_camera_thread():
    """Start YOLO person detection in a background daemon thread."""
    try:
        from vision.person_detector import YoloPersonDetector
    except ImportError:
        print(
            "AVISO: No se pudo iniciar la cámara. "
            "Instala las dependencias: pip install ultralytics opencv-python"
        )
        return None

    if not YoloPersonDetector.is_available():
        print(
            "AVISO: ultralytics u opencv-python no están instalados. "
            "La detección por cámara no estará activa."
        )
        return None

    detector = YoloPersonDetector()

    thread = threading.Thread(
        target=detector.run_continuous,
        args=(_camera_detection_callback,),
        daemon=True,
        name="yolo-camera",
    )
    thread.start()
    print("[Cámara] Detección de personas con YOLO iniciada en segundo plano.")
    return thread


# ======================================================================
# Main loops
# ======================================================================


def chat_to_voice():
    """Text input loop: keyboard → LLM → TTS."""
    print("--- UNEV Hologram (Teclado) ---")
    print("Type a message to the AI.")
    print(
        "Commands: 'quit', 'exit', 'ayuda', 'backend', 'saludar', 'persona', 'grupo', 'formal'."
    )
    print("Modes: 'modo jueces', 'modo expo', 'modo admisiones', 'modo normal'.")
    print(get_backend_status())
    print("Ollama recomendado para este setup: gemma4:e4b.")

    while True:
        hologram.set_state("idle")
        user_input = input("\nYou: ").strip()

        if not user_input:
            continue

        if normalize_text(user_input) in ["quit", "exit", "salir"]:
            break

        global ai_busy
        ai_busy = True
        try:
            command_response = handle_command(user_input)
            if command_response:
                speak(command_response)
                continue

            print("The AI is thinking...")
            hologram.set_state("thinking")
            reply = ask_ai(user_input, CURRENT_MODE)
            speak(reply)
        finally:
            ai_busy = False


def voice_loop():
    """Voice input loop: microphone → Whisper → LLM → TTS (Regla B: sounddevice)."""
    try:
        from stt.listener import WhisperListener, get_stt_status
    except ImportError:
        print(
            "ERROR: No se pudo iniciar el modo voz. "
            "Instala las dependencias: pip install faster-whisper sounddevice numpy"
        )
        print("Iniciando en modo teclado como fallback...")
        chat_to_voice()
        return

    if not WhisperListener.is_available():
        print(
            "ERROR: faster-whisper o sounddevice no están instalados. "
            "Ejecuta: pip install faster-whisper sounddevice numpy"
        )
        print("Iniciando en modo teclado como fallback...")
        chat_to_voice()
        return

    listener = WhisperListener()

    print("--- UNEV Hologram (Voz) ---")
    print("Habla al micrófono. Di 'salir' o 'exit' para terminar.")
    print(get_stt_status())
    print(get_backend_status())
    print("Ollama recomendado para este setup: gemma4:e4b.")

    # Pre-load the Whisper model so the first utterance is fast
    print("[STT] Preparando modelo de voz...")
    listener._load_model()

    global ai_busy
    ai_busy = True

    while True:
        print("\n[STT] Esperando tu voz...")

        # Esperar a que el TTS termine de hablar antes de escuchar al micrófono
        speak_lock.acquire()
        speak_lock.release()
        # Pequeña pausa para que el eco de las bocinas se disipe
        time.sleep(0.8)

        ai_busy = False  # El holograma está libre justo cuando empieza a escuchar
        hologram.set_state("listening")
        user_input = listener.listen_once()
        ai_busy = True  # El holograma vuelve a estar ocupado procesando el input

        if not user_input:
            continue

        if normalize_text(user_input) in ["quit", "exit", "salir"]:
            print("¡Hasta pronto!")
            break

        try:
            command_response = handle_command(user_input)
            if command_response:
                speak(command_response)
                continue

            print("The AI is thinking...")
            hologram.set_state("thinking")
            reply = ask_ai(user_input, CURRENT_MODE)
            speak(reply)
        finally:
            pass  # ai_busy se controla al inicio del loop


# ======================================================================
# Entry point
# ======================================================================


def main():
    """Parse flags and run the appropriate loop."""
    use_voice = (
        "--voice" in sys.argv or os.getenv("HOLOGRAM_INPUT", "").lower() == "voice"
    )
    use_camera = "--camera" in sys.argv or os.getenv("HOLOGRAM_CAMERA", "") == "1"

    # Conecta el holograma físico (no-op si HOLOGRAM_TCP_IP no está definida).
    hologram.start()

    if use_camera:
        start_camera_thread()

    try:
        if use_voice:
            voice_loop()
        else:
            chat_to_voice()
    finally:
        hologram.close()


if __name__ == "__main__":
    main()
