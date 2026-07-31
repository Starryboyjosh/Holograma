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
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

# Contexto de cámara: lógica neutra compartida (rompe el ciclo call↔llm_backend).
from camera_context import build_camera_context as _build_camera_context
from hologram_controller import create_hologram_manager
from llm_backend import (
    COT_BLOCK_RE,
    COT_LOOSE_TAG_RE,
    generate_reply,
    get_backend_status,
    get_selected_backend,
    iter_reply_tokens,
)
from prompt_package import build_university_context
from skills.appearance import get_cordial_observation
from skills.event_mode import get_greeting, get_system_prompt
from skills.presence import PresenceManager
from skills.router import route_local_skill
from skills.university import normalize_text
from utils import (
    _is_quiet,
    apply_config_to_env,
    configure_utf8_stdio,
    load_config,
    pop_ready_speech,
)

configure_utf8_stdio()

# Fix for Wayland/CachyOS.
os.environ["QT_QPA_PLATFORM"] = "xcb"

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Cargar configuración unificada desde config.json (Regla A: Path).
# Mantiene la precedencia: .env (ya en os.environ) gana; config.json es fallback.
CONFIG_FILE = BASE_DIR / "config.json"
apply_config_to_env(load_config(CONFIG_FILE))

CURRENT_MODE = os.getenv("HOLOGRAM_MODE", "normal")
DEFAULT_PIPER_MODEL = "es_MX-claude-high.onnx"
presence_manager = PresenceManager(
    greeting_cooldown_seconds=120, absence_reset_seconds=20
)
speak_lock = threading.Lock()
ai_busy = False
_hologram_paused = False


def stop_all_tts_processes():
    """Attempt to terminate any running TTS or audio players on Linux."""
    import platform
    import subprocess

    if platform.system() == "Linux":
        for proc in ["aplay", "paplay", "piper", "espeak-ng", "espeak", "spd-say"]:
            try:
                subprocess.run(["killall", "-9", proc], capture_output=True)
            except Exception:
                pass


def pause_hologram():
    """Pause hologram activity: stop speaking, listening and seeing."""
    global _hologram_paused
    _hologram_paused = True
    stop_all_tts_processes()
    print("[Holograma] IA Pausada por completo.")


def resume_hologram():
    """Resume hologram activity."""
    global _hologram_paused
    _hologram_paused = False
    print("[Holograma] IA Reanudada.")


# Puente con el ventilador holográfico físico (TCP). Deshabilitado (no-op) si
# HOLOGRAM_TCP_IP no está definida — la IA corre igual sin dispositivo conectado.
hologram = create_hologram_manager()


# ======================================================================
# TTS helpers
# ======================================================================


def clean_for_tts(text):
    """Remove characters that can sound awkward when read by a TTS engine.

    Última red del TTS: el stream ya llega filtrado por `_CotStreamFilter`, pero
    esto protege también las llamadas no-streaming. Usa el mismo juego de tags
    que `llm_backend` —conocía sólo `<think>` y dejaba pasar `<reasoning>` y
    compañía al altavoz— incluidas las etiquetas sueltas sin pareja.
    """
    replacements = {
        "*": "",
        "[": "",
        "]": "",
        "`": "",
        "#": "",
        "_": "",
    }

    clean_text = COT_BLOCK_RE.sub("", text)
    clean_text = COT_LOOSE_TAG_RE.sub("", clean_text)
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
        # Si la ruta apunta al wrapper antiguo en la raíz pero está en scripts/
        if "piper_wrapper.sh" in configured_command and "scripts/piper_wrapper.sh" not in configured_command:
            fallback_wrapper = BASE_DIR / "scripts" / "piper_wrapper.sh"
            if fallback_wrapper.exists():
                return [str(fallback_wrapper)]
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
        if not _is_quiet():
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
        if not _is_quiet():
            print(f"Error ejecutando PowerShell: {error}")
        return False

    if result.stdout.strip():
        if not _is_quiet():
            print(result.stdout.strip())

    if result.returncode != 0:
        if result.stderr.strip():
            if not _is_quiet():
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
            ["pw-play", wav_path],
            ["paplay", wav_path],
            ["aplay", wav_path],
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
            if not _is_quiet():
                print(f"AVISO: No pude usar {player_command[0]} para audio: {error}")
            continue

        if result.returncode == 0:
            return True

        if result.stderr.strip():
            if not _is_quiet():
                print(f"AVISO: {player_command[0]} falló: {result.stderr.strip()}")

    if not _is_quiet():
        print(
            "AVISO: No encontré reproductor de audio compatible. "
            "En Linux instala aplay, paplay, pw-play, ffplay o mpv."
        )
    return False


# Piper en proceso: cargar el modelo UNA vez evita el cold-start del subprocess
# en cada frase (principal causa del hueco LLM→voz).
_piper_voice = None
_piper_voice_lock = threading.Lock()
_piper_voice_model_path: str | None = None


def _piper_available():
    """True si Piper y su modelo de voz están listos para usarse."""
    try:
        model_path = get_piper_model_path()
        if not Path(model_path).exists() or not Path(f"{model_path}.json").exists():
            return False
        # API Python in-process o CLI.
        if importlib.util.find_spec("piper") is not None:
            return True
        return bool(get_piper_command_args())
    except Exception:
        return False


def _get_piper_voice():
    """Carga (o reutiliza) ``PiperVoice`` del paquete ``piper`` en este proceso."""
    global _piper_voice, _piper_voice_model_path
    model_path = str(Path(get_piper_model_path()).resolve())
    with _piper_voice_lock:
        if _piper_voice is not None and _piper_voice_model_path == model_path:
            return _piper_voice
        try:
            from piper import PiperVoice
        except ImportError:
            return None
        t0 = time.monotonic()
        if not _is_quiet():
            print(f"[TTS] Cargando Piper in-process: {Path(model_path).name}...")
        try:
            # espeak_data del bundle local si existe.
            espeak = BASE_DIR / "piper" / "piper" / "espeak-ng-data"
            kwargs = {}
            if espeak.is_dir():
                kwargs["espeak_data_dir"] = str(espeak)
            _piper_voice = PiperVoice.load(model_path, **kwargs)
            _piper_voice_model_path = model_path
            if not _is_quiet():
                print(f"[TTS] Piper listo en {time.monotonic() - t0:.2f}s (reutilizado en cada frase).")
            return _piper_voice
        except Exception as error:
            if not _is_quiet():
                print(f"[TTS] No se pudo cargar Piper in-process ({error}); usaré CLI.")
            _piper_voice = None
            _piper_voice_model_path = None
            return None


def warm_tts():
    """Precarga Piper al arrancar el bucle de voz (evita el 1.er hueco largo)."""
    if not _piper_available():
        return
    try:
        _get_piper_voice()
    except Exception:
        pass


def _piper_synth_to_wav_python(text):
    """Síntesis in-process con PiperVoice → WAV temporal. None si no aplica."""
    voice = _get_piper_voice()
    if voice is None:
        return None
    text = (text or "").strip()
    if not text:
        return None

    temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav_path = Path(temp_wav.name)
    temp_wav.close()
    t0 = time.monotonic()
    try:
        import wave

        with wave.open(str(wav_path), "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        if not _is_quiet():
            print(f"[TTS] synth in-process {len(text)} chars en {time.monotonic() - t0:.2f}s")
        return wav_path
    except Exception as error:
        if not _is_quiet():
            print(f"[TTS] Falló síntesis in-process ({error}); probando CLI.")
        wav_path.unlink(missing_ok=True)
        return None


def _piper_synth_to_wav_cli(text):
    """Síntesis vía subprocess (fallback si no hay API Python)."""
    piper_command_args = get_piper_command_args()
    if not piper_command_args:
        return None

    model_path = get_piper_model_path()
    if not Path(model_path).exists() or not Path(f"{model_path}.json").exists():
        return None

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

        t0 = time.monotonic()
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
            if not _is_quiet():
                print("AVISO: Piper no pudo generar la voz.")
                if result.stderr.strip():
                    print(result.stderr.strip())
            wav_path.unlink(missing_ok=True)
            return None

        if not _is_quiet():
            print(f"[TTS] synth CLI {len(text)} chars en {time.monotonic() - t0:.2f}s")
        return wav_path
    except subprocess.TimeoutExpired:
        if not _is_quiet():
            print("AVISO: Piper tardó demasiado generando la voz.")
        wav_path.unlink(missing_ok=True)
        return None
    except Exception as error:
        if not _is_quiet():
            print(f"Error generando voz con Piper: {error}")
        wav_path.unlink(missing_ok=True)
        return None


def _piper_synth_to_wav(text):
    """Sintetiza *text* a un WAV temporal con Piper. Devuelve la ruta (Path) o
    ``None`` si Piper no está disponible o falla. NO reproduce: separar síntesis
    de reproducción permite ir generando el siguiente fragmento mientras suena el
    actual (pipeline), evitando la pausa tras cada punto.

    Prefiere la API Python in-process (modelo cargado una vez); si no, CLI.
    """
    if not (text or "").strip():
        return None
    prefer_cli = os.getenv("PIPER_FORCE_CLI", "").lower() in ("1", "true", "yes")
    if not prefer_cli:
        wav = _piper_synth_to_wav_python(text)
        if wav is not None:
            return wav
    return _piper_synth_to_wav_cli(text)


def speak_with_piper(text):
    """Use Piper TTS and play the generated WAV file on the current OS."""
    wav_path = _piper_synth_to_wav(text)
    if wav_path is None:
        if not _is_quiet():
            print(
                "AVISO: No pude generar voz con Piper. Intentaré una voz nativa del sistema."
            )
            print(get_piper_install_hint())
        return False
    try:
        return play_wav_file(str(wav_path))
    finally:
        wav_path.unlink(missing_ok=True)  # Regla A


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
                if not _is_quiet():
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
            if not _is_quiet():
                print(f"AVISO: No pude usar spd-say: {error}")

    return False


def _split_into_chunks(text):
    """Divide texto limpio en fragmentos TTS (misma heurística que el stream).

    Usa ``pop_ready_speech`` (fuente única en ``utils``) para no divergir del
    camino streaming de ``ConversationService`` / ``speak_streaming_from_llm``.
    """
    text = clean_for_tts(text)
    if not text:
        return []
    # El regex de cláusulas exige whitespace tras la puntuación.
    buf = text if text[-1:].isspace() else text + " "
    chunks: list[str] = []
    first = True
    while True:
        ready, buf, first = pop_ready_speech(buf, first)
        if not ready:
            break
        chunks.extend(ready)
    remainder = buf.strip()
    if remainder:
        chunks.append(remainder)
    return chunks


def _speak_chunk_os(chunk):
    """Reproduce un fragmento con el TTS nativo del SO (fallback sin Piper)."""
    tts_backend = os.getenv("TTS_BACKEND", "auto").lower().strip()
    system_name = platform.system()
    try:
        # Windows nativo o WSL → System.Speech (una sola ruta).
        if (
            system_name == "Windows" or is_wsl()
        ) and tts_backend in ("auto", "windows", "native"):
            if speak_with_windows_voice(chunk):
                return True
        if system_name == "Linux" and tts_backend in (
            "auto",
            "linux",
            "native",
            "espeak",
        ):
            # En WSL, si Windows TTS falló, aún se puede intentar espeak.
            if speak_with_linux_tts(chunk):
                return True
        if not _is_quiet():
            print(f"AVISO: No pude reproducir voz para el fragmento: {chunk}")
    except Exception as e:
        if not _is_quiet():
            print(f"Error en el reproductor de voz: {e}")
    return False


def _speak_one_chunk(chunk: str) -> None:
    """Sintetiza y reproduce un solo fragmento (sin hilo de pipeline)."""
    if _hologram_paused or not (chunk or "").strip():
        return
    if not _is_quiet():
        print(f"\nSpeaking chunk: {chunk}")
    tts_backend = os.getenv("TTS_BACKEND", "auto").lower().strip()
    use_piper = tts_backend in ("auto", "piper") and _piper_available()
    if use_piper:
        if speak_with_piper(chunk):
            return
        # Piper falló al generar/reproducir → nativo.
    _speak_chunk_os(chunk)


def _render_chunks(chunks):
    """Sintetiza y reproduce los fragmentos de voz.

    Un solo fragmento: camino directo (sin cola/hilo). Varios + Piper: pipeline
    (sintetiza el siguiente mientras suena el actual). Sin Piper: TTS nativo.
    """
    if not chunks:
        return
    tts_backend = os.getenv("TTS_BACKEND", "auto").lower().strip()
    use_piper = tts_backend in ("auto", "piper") and _piper_available()

    if not use_piper or len(chunks) == 1:
        for chunk in chunks:
            if _hologram_paused:
                return
            _speak_one_chunk(chunk)
        return

    # --- Pipeline Piper multi-fragmento: síntesis adelantada ---
    wav_q = queue.Queue(maxsize=2)
    _SENTINEL = object()

    def _synth():
        for chunk in chunks:
            if _hologram_paused:
                break
            wav_q.put((chunk, _piper_synth_to_wav(chunk)))
        wav_q.put(_SENTINEL)

    threading.Thread(target=_synth, args=(), daemon=True).start()

    while True:
        item = wav_q.get()
        if item is _SENTINEL:
            break
        chunk, wav_path = item
        if _hologram_paused:
            if wav_path is not None:
                wav_path.unlink(missing_ok=True)
            continue
        if not _is_quiet():
            print(f"\nSpeaking chunk: {chunk}")
        if wav_path is None:
            _speak_chunk_os(chunk)
        else:
            try:
                play_wav_file(str(wav_path))
            finally:
                wav_path.unlink(missing_ok=True)


def speak(text, blocking=True, *, end_idle=True):
    """Speak text using Piper when possible, with OS-native fallbacks.

    Utiliza segmentación inteligente por cláusulas y oraciones.
    ``end_idle=False`` deja el holograma en "speaking" (turno multi-fragmento).
    """
    if _hologram_paused:
        return
    chunks = _split_into_chunks(text)
    if not chunks:
        return

    # Evitar reproducción superpuesta usando el speak_lock
    acquired = speak_lock.acquire(blocking=blocking)
    if not acquired:
        if not _is_quiet():
            print(f"[TTS] Omitiendo habla para evitar traslape: {text[:60]}...")
        return

    # El holograma muestra la animación de "hablando" mientras dura el TTS.
    hologram.set_state("speaking")

    def _run():
        try:
            _render_chunks(chunks)
        finally:
            speak_lock.release()
            if end_idle:
                hologram.set_state("idle")

    if blocking:
        _run()
    else:
        # No-bloqueante (p. ej. web): reproducir en un hilo; libera el lock al final.
        threading.Thread(target=_run, daemon=True).start()


# Cláusulas sintetizadas por adelantado durante la reproducción. Con 2 basta
# para tapar el hueco entre frases sin acumular audio que habría que tirar si el
# usuario interrumpe.
_TTS_PIPELINE_DEPTH = 2


def speak_streaming_from_llm(token_iter, *, on_text=None, on_speaking=None) -> str:
    """Habla cláusulas en cuanto el LLM las produce (sin esperar al final).

    Mantiene el lock/estado de voz durante todo el turno para no parpadear
    a idle entre frases. Devuelve el texto completo post-procesado.

    **Pipeline de 3 etapas.** Antes esta función sintetizaba y reproducía cada
    cláusula en línea, dentro del bucle de tokens:

        cláusula 1: [sintetiza][reproduce] cláusula 2: [sintetiza][reproduce] …

    Con Piper la síntesis tarda cientos de ms, así que entre frase y frase había
    un silencio audible, y además el bucle bloqueado dejaba de consumir tokens
    del LLM. Ahora las tres etapas van en paralelo:

        tokens ─► cola de cláusulas ─► hilo de síntesis ─► cola de wavs ─► hilo de audio

    La cláusula N+1 se sintetiza mientras suena la N, así que el hueco
    desaparece; y el bucle de tokens no se bloquea nunca detrás del audio.
    ``_render_chunks`` ya hacía esto para el camino no-streaming, pero la ruta
    de conversación —la que se oye en el kiosko— no lo usaba.
    """
    from llm_backend import _postprocess_reply  # postproceso ligero al final

    if _hologram_paused:
        return ""

    acquired = speak_lock.acquire(blocking=True)
    if not acquired:
        return ""

    hologram.set_state("speaking")
    speech_buf = ""
    first = True
    parts: list[str] = []
    t0 = time.monotonic()

    tts_backend = os.getenv("TTS_BACKEND", "auto").lower().strip()
    use_piper = tts_backend in ("auto", "piper") and _piper_available()

    clause_q: queue.Queue = queue.Queue()
    wav_q: queue.Queue = queue.Queue(maxsize=_TTS_PIPELINE_DEPTH)
    _SENTINEL = object()
    # Estado compartido con los hilos; solo ellos escriben cada clave.
    state = {"spoke_any": False, "marked": False, "t_first": None}

    def _synth_worker():
        """Cláusula → WAV. Va por delante de la reproducción."""
        try:
            while True:
                piece = clause_q.get()
                if piece is _SENTINEL:
                    break
                if _hologram_paused:
                    continue  # drenar sin sintetizar
                try:
                    wav = _piper_synth_to_wav(piece) if use_piper else None
                except Exception as error:
                    # Que Piper reviente en una cláusula no debe cortar el turno:
                    # se emite igual y la reproduce la voz del sistema.
                    if not _is_quiet():
                        print(f"[TTS] Fallo sintetizando un fragmento: {error}")
                    wav = None
                wav_q.put((piece, wav))
        finally:
            wav_q.put(_SENTINEL)

    def _play_worker():
        """WAV → altavoz, en orden."""
        while True:
            item = wav_q.get()
            if item is _SENTINEL:
                return
            piece, wav = item
            if _hologram_paused:
                if wav is not None:
                    wav.unlink(missing_ok=True)
                continue
            if state["t_first"] is None:
                state["t_first"] = time.monotonic()
                if not _is_quiet():
                    print(
                        f"[TTS] primer audio a {state['t_first'] - t0:.2f}s "
                        f"desde inicio del stream LLM",
                        flush=True,
                    )
            if not state["marked"] and on_speaking is not None:
                try:
                    on_speaking()
                except Exception:
                    pass
                state["marked"] = True
            if not _is_quiet():
                print(f"\nSpeaking chunk: {piece}")
            # Un fallo reproduciendo UNA cláusula no puede matar el hilo: si
            # muriera, nadie vaciaría `wav_q`, el hilo de síntesis se quedaría
            # bloqueado en un `put()` lleno y el `join()` colgaría el kiosko.
            try:
                if wav is None:
                    # Sin Piper, o su síntesis falló: voz nativa del sistema.
                    _speak_chunk_os(piece)
                else:
                    try:
                        play_wav_file(str(wav))
                    finally:
                        wav.unlink(missing_ok=True)
                state["spoke_any"] = True
            except Exception as error:
                if not _is_quiet():
                    print(f"[TTS] Fallo reproduciendo un fragmento: {error}")

    synth_thread = threading.Thread(target=_synth_worker, daemon=True)
    play_thread = threading.Thread(target=_play_worker, daemon=True)
    synth_thread.start()
    play_thread.start()

    try:
        for token in token_iter:
            if _hologram_paused:
                break
            if not token:
                continue
            parts.append(token)
            if on_text is not None:
                try:
                    on_text(token)
                except Exception:
                    pass
            speech_buf += token
            # No limpiar todo el buffer (rompería cláusulas a medias); solo
            # strip de espacios extremos al cortar.
            ready, speech_buf, first = pop_ready_speech(speech_buf, first)
            for piece in ready:
                piece = clean_for_tts(piece)
                if piece:
                    clause_q.put(piece)

        remainder = clean_for_tts(speech_buf)
        if remainder and not _hologram_paused:
            clause_q.put(remainder)
    finally:
        # Cerrar el pipeline y esperar a que termine el audio antes de soltar el
        # lock: si no, el siguiente turno pisaría el final de este.
        clause_q.put(_SENTINEL)
        synth_thread.join()
        play_thread.join()
        speak_lock.release()
        hologram.set_state("idle")

    full = _postprocess_reply("".join(parts))
    if not state["spoke_any"] and full.strip() and not _hologram_paused:
        # Fallback: una sola pasada si no hubo cláusulas. El audio es
        # best-effort; el contrato de esta función es DEVOLVER el texto. Si el
        # dispositivo de sonido está roto, el visitante debe seguir viendo la
        # respuesta escrita en pantalla en vez de recibir un error.
        try:
            speak(full)
        except Exception as error:
            if not _is_quiet():
                print(f"[TTS] No se pudo locutar la respuesta: {error}")
    return full


# ======================================================================
# AI / LLM helpers
# ======================================================================

_last_camera_analysis = {}
_visual_keywords = [
    "ves",
    "ver ",
    "verme",
    "verte",
    "mir",
    "cámar",
    "camar",
    "frent",
    "describe",
    "descríbeme",
    "qué hay",
    "que hay",
    "qué ves",
    "que ves",
    "qué llevo",
    "que llevo",
    "delante",
    "enfrente",
    "visible",
    "veo",
    "ven",
    "algo ahí",
    "alguien",
    "quién está",
    "quien esta",
    "objeto",
    "detect",
    "yolo",
    "persona",
    "gente",
    "uniforme",
    "vestiment",
    "vestido",
    "ropa",
    "camis",
    "puedes ver",
    "me ves",
    "nos ves",
]


def _is_visual_question(user_input):
    text = user_input.lower().strip()
    for kw in _visual_keywords:
        if kw in text:
            return True
    return False


def _is_greeting(user_input):
    text = user_input.lower().strip()
    greeting_keywords = [
        "hola",
        "buenos dias",
        "buenos días",
        "buenas tardes",
        "buenas noches",
        "saludo",
        "cómo estás",
        "como estas",
        "qué tal",
        "que tal",
        "buen dia",
        "buen día",
    ]
    for kw in greeting_keywords:
        if kw in text:
            return True
    return False


def _camera_context_for_prompt(user_input: str) -> str | None:
    """Contexto de cámara listo para el LLM (misma lógica en ask_ai y stream)."""
    visual_q = _is_visual_question(user_input)

    # Pregunta visual + cámara configurada: no dejar el hilo YOLO apagado
    # (la UI a veces llama /api/camera enabled=false y se pierde el uniforme).
    if visual_q and os.getenv("HOLOGRAM_CAMERA", "0") == "1":
        ensure_camera_for_vision(wait_s=2.5)

    camera_context = None
    if _last_camera_analysis:
        # Objetos/uniforme solo si el usuario pregunta por ellos (no en saludos).
        camera_context = _build_camera_context(
            _last_camera_analysis, include_objects=visual_q
        )
    elif os.getenv("HOLOGRAM_CAMERA", "0") == "1":
        if not is_camera_detection_running():
            camera_context = (
                "La cámara/visión está apagada o no entrega frames. "
                "Di con naturalidad que no puedes ver ahora (pide encender la cámara "
                "en la interfaz). No inventes uniformes ni personas."
            )
        else:
            camera_context = (
                "Aún no hay un análisis visual reciente (el detector está arrancando). "
                "No inventes lo que ves; si preguntan por el uniforme u objetos, "
                "di con naturalidad que ahora mismo no puedes confirmarlo."
            )

    if camera_context and visual_q and not _is_quiet():
        co = (_last_camera_analysis or {}).get("custom_objects") or []
        labels = [o.get("label") for o in co if isinstance(o, dict)]
        print(
            f"[Cámara→LLM] running={is_camera_detection_running()} "
            f"custom={labels or '[]'} "
            f"persons={(_last_camera_analysis or {}).get('person_count', 0)}"
        )
    return camera_context


def ask_ai(user_input, mode=None):
    mode = mode or CURRENT_MODE

    if get_selected_backend() == "local_only":
        local_response = route_local_skill(user_input)
        if local_response:
            return local_response

    return generate_reply(
        user_input=user_input,
        system_prompt=get_system_prompt(mode),
        # Sólo las secciones que la pregunta necesita, decididas en el único
        # ensamblador (`prompt_package`), igual que en la ruta web.
        university_context=build_university_context(user_input, event_mode=mode),
        camera_context=_camera_context_for_prompt(user_input),
        event_mode=mode,
    )


_hologram_turn_orchestrator = None


def _get_hologram_turn_orchestrator():
    """Construye una sola capa semántica sobre el adaptador/director actual."""
    global _hologram_turn_orchestrator
    director = getattr(hologram, "_director", None)
    if director is None:
        return None
    if _hologram_turn_orchestrator is None or _hologram_turn_orchestrator._director is not director:
        from app.hologram.conversation_orchestrator import HologramConversationOrchestrator
        from app.hologram.media_router import MediaRouter

        _hologram_turn_orchestrator = HologramConversationOrchestrator(MediaRouter(director.config), director)
    return _hologram_turn_orchestrator


def ask_ai_and_speak(user_input, mode=None) -> str:
    """Stream LLM + TTS por cláusulas (menor latencia a primera voz)."""
    mode = mode or CURRENT_MODE

    orchestrator = _get_hologram_turn_orchestrator()
    context_id = None
    if orchestrator is not None:
        context_id = orchestrator.start_turn(user_input, mode=mode)
    try:
        if get_selected_backend() == "local_only":
            local_response = route_local_skill(user_input)
            if local_response:
                if orchestrator is not None:
                    orchestrator.observe_response_text(local_response, context_id)
                    orchestrator.mark_speaking()
                speak(local_response)
                return local_response

        tokens = iter_reply_tokens(
            user_input=user_input,
            system_prompt=get_system_prompt(mode),
            university_context=build_university_context(user_input, event_mode=mode),
            camera_context=_camera_context_for_prompt(user_input),
            # El modo ya está dentro del system_prompt; se pasa aparte sólo para
            # que la métrica del turno pueda registrarlo.
            event_mode=mode,
        )
        return speak_streaming_from_llm(
            tokens,
            on_text=(lambda text: orchestrator.observe_response_text(text, context_id)) if orchestrator else None,
            on_speaking=orchestrator.mark_speaking if orchestrator else None,
        )
    except Exception as error:
        if orchestrator is not None:
            orchestrator.fail_turn(error, context_id)
        raise
    finally:
        if orchestrator is not None:
            orchestrator.finish_turn(context_id)


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


_last_custom_speak_times = {}

# Instancia activa del detector de cámara (para exponer el feed anotado al frontend).
_camera_detector = None
# Hilo activo de la cámara, para poder detenerlo y liberar el dispositivo.
_camera_thread = None


def get_latest_camera_jpeg():
    """Return the latest annotated camera frame (JPEG bytes) or None."""
    if _camera_detector is None:
        return None
    return _camera_detector.get_latest_jpeg()


def camera_feed_subscribe():
    """Registra un cliente del feed de video (activa la codificación JPEG).

    El detector solo codifica el cuadro anotado mientras haya al menos un cliente
    viendo `/api/video_feed`; sin suscriptores ahorra el imencode por cuadro.
    """
    detector = _camera_detector
    if detector is not None:
        detector.feed_subscribe()


def camera_feed_unsubscribe():
    """Da de baja un cliente del feed de video."""
    detector = _camera_detector
    if detector is not None:
        detector.feed_unsubscribe()


def _camera_detection_callback(event, count, analysis=None):
    """Handle YOLO detection events from the background camera thread."""
    global ai_busy, _last_camera_analysis, _last_custom_speak_times, _person_present
    if _hologram_paused:
        return
    analysis = analysis or {}
    # Siempre refrescar el análisis para el LLM (también en analysis_update /
    # person_still_present). Sin esto el contexto se congelaba en el primer frame.
    _last_camera_analysis = analysis
    # Presencia para el modo presentación (se actualiza aunque la IA esté ocupada).
    if event in ("person_entered", "group_detected"):
        _person_present = True
    elif event == "person_left":
        _person_present = False
    elif event == "analysis_update":
        if count and count > 0:
            _person_present = True
        # Solo actualiza contexto; no saluda ni habla.
        return
    if ai_busy or speak_lock.locked():
        if event == "person_left":
            presence_manager.force_person_left()
            hologram.set_state("idle")
            print("[Cámara] La persona se fue. Vuelvo a modo espera (sin interrumpir).")
        return

    if event == "person_entered":
        if presence_manager.should_greet(True):
            # Saludo genérico de presencia: el holograma reconoce que llegó una
            # persona, sin atribuir ninguna identidad concreta.
            speak(get_greeting(CURRENT_MODE), blocking=False)

    elif event == "group_detected":
        if presence_manager.should_greet_group():
            observation = get_cordial_observation("grupo")
            speak(observation, blocking=False)

    elif event == "person_left":
        presence_manager.force_person_left()
        hologram.set_state("idle")
        print("[Cámara] La persona se fue. Vuelvo a modo espera.")

    elif event == "custom_object_detected":
        # Por defecto NO anunciar en voz: el STT se oye a sí mismo y el
        # visitante no pidió el uniforme. Activa con HOLOGRAM_ANNOUNCE_CUSTOM=1.
        if os.getenv("HOLOGRAM_ANNOUNCE_CUSTOM", "0").lower() not in (
            "1",
            "true",
            "yes",
        ):
            return
        custom_objs = analysis.get("custom_objects", [])
        labels = list({o["label"] for o in custom_objs if o.get("label")})
        now = time.time()
        labels_to_speak = [
            lbl for lbl in labels if now - _last_custom_speak_times.get(lbl, 0) > 60.0
        ]
        if not labels_to_speak:
            return
        for lbl in labels_to_speak:
            _last_custom_speak_times[lbl] = now
        desc = ", ".join(labels_to_speak[:3])

        def _delayed_speak():
            time.sleep(1.0)
            speak(f"¡Mira, detecto a {desc}!", blocking=False)

        threading.Thread(target=_delayed_speak, daemon=True).start()


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
            "AVISO: ultralytics (YOLOE) u opencv-python no están instalados. "
            "La detección por cámara no estará activa."
        )
        return None

    global _camera_detector, _camera_thread

    # Evitar dos hilos de cámara compitiendo por el mismo dispositivo.
    if _camera_thread is not None and _camera_thread.is_alive():
        print("[Cámara] La detección ya estaba activa.")
        return _camera_thread

    detector = YoloPersonDetector()
    _camera_detector = detector

    thread = threading.Thread(
        target=detector.run_continuous,
        args=(_camera_detection_callback,),
        daemon=True,
        name="yolo-camera",
    )
    thread.start()
    _camera_thread = thread
    print(
        f"[Cámara] Detección YOLOE iniciada "
        f"({getattr(detector, 'model_name', 'yoloe-26n-seg.pt')})."
    )
    return thread


def stop_camera_thread(timeout=5.0):
    """Detén la detección y libera la cámara (apagar la cámara = liberarla).

    Señala la parada cooperativa del detector; el bucle sale y el context manager
    de ``Camera`` libera el dispositivo. Idempotente.

    Importante: al parar se resetea presencia y el último análisis. Si no, el modo
    presentación se queda con ``_person_present=True`` y sigue escuchando ruido
    (alucinaciones STT), y el LLM cree que hay visión cuando no hay.
    """
    global _camera_detector, _camera_thread, _last_camera_analysis, _person_present

    detector = _camera_detector
    thread = _camera_thread
    if detector is not None:
        detector.stop()
    if thread is not None and thread.is_alive():
        thread.join(timeout=timeout)

    _camera_thread = None
    _camera_detector = None
    _person_present = False
    _last_camera_analysis = {}
    print("[Cámara] Detección detenida y cámara liberada.")
    return True


def is_camera_detection_running() -> bool:
    """True si el hilo YOLO está vivo."""
    t = _camera_thread
    return t is not None and t.is_alive()


def ensure_camera_for_vision(wait_s: float = 2.5) -> bool:
    """Si ``HOLOGRAM_CAMERA=1`` y el hilo murió, lo relanza (p. ej. tras apagar UI).

    Espera un poco a un primer análisis para preguntas visuales.
    """
    if os.getenv("HOLOGRAM_CAMERA", "0") != "1":
        return False
    if is_camera_detection_running():
        return True
    print("[Cámara] Visión requerida pero el hilo estaba parado; reiniciando…")
    start_camera_thread()
    deadline = time.time() + max(0.0, wait_s)
    while time.time() < deadline:
        if _last_camera_analysis:
            return True
        time.sleep(0.15)
    return is_camera_detection_running()


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
    print(
        "Ollama recomendado para este equipo: gemma3:1b (el mas rapido en CPU; modelos mayores hacen timeout)."
    )

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
            orchestrator = _get_hologram_turn_orchestrator()
            context_id = orchestrator.start_turn(user_input, mode=CURRENT_MODE) if orchestrator else None
            try:
                reply = ask_ai(user_input, CURRENT_MODE)
                if orchestrator is not None:
                    orchestrator.observe_response_text(reply, context_id)
                    orchestrator.mark_speaking()
                speak(reply)
            except Exception as error:
                if orchestrator is not None:
                    orchestrator.fail_turn(error, context_id)
                raise
            finally:
                if orchestrator is not None:
                    orchestrator.finish_turn(context_id)
        finally:
            ai_busy = False


# ======================================================================
# Activación de la escucha (push-to-talk / modo presentación)
# ======================================================================
#
# Modos vía HOLOGRAM_VOICE_TRIGGER (cambiables en caliente con set_trigger_mode):
#   ptt           -> push-to-talk: escucha SOLO cuando se solicita (botón del
#                    orbe en la WebApp o ENTER en la terminal). Lo más fiable en
#                    lugares ruidosos.
#   presentation  -> el holograma escucha y responde de forma continua, pero solo
#                    mientras la cámara detecta gente delante. Manos libres.
#   auto          -> escucha continua siempre (sin depender de la cámara).

# Evento que dispara una escucha puntual. Lo activan el botón de la WebApp
# (vía main.py -> request_listen) o ENTER en la terminal.
_listen_requested = threading.Event()

# main.py lo pone en True al lanzar voice_loop en un hilo del servidor web, para
# no leer stdin (la terminal del servidor) como push-to-talk.
WEB_MODE = False

# True mientras voice_loop está vivo (el botón PTT de la WebApp lo necesita).
_voice_loop_running = False

# main.py asigna manager.broadcast_threadsafe para emitir estados de voz a la UI.
_ws_emit = None

# Modo de activación actual (dinámico: la WebApp puede cambiarlo sin reiniciar).
_voice_trigger_mode = os.getenv("HOLOGRAM_VOICE_TRIGGER", "ptt").lower().strip()
if _voice_trigger_mode not in ("ptt", "presentation", "auto"):
    _voice_trigger_mode = "ptt"

# Lo actualiza la cámara (_camera_detection_callback): ¿hay alguien delante?
_person_present = False


def _emit_voice_event(payload: dict) -> None:
    """Difunde un evento de voz a la WebApp si hay puente WS (main.py)."""
    fn = _ws_emit
    if callable(fn):
        try:
            fn(payload)
        except Exception as error:  # noqa: BLE001 - no tumbar el hilo de voz
            if not _is_quiet():
                print(f"[VOZ] No se pudo emitir evento WS: {error}")


def request_listen():
    """Solicita una escucha puntual (push-to-talk remoto, p. ej. la WebApp)."""
    if WEB_MODE and not _voice_loop_running:
        _emit_voice_event(
            {
                "type": "error",
                "message": (
                    "El modo voz no está activo en el servidor "
                    "(HOLOGRAM_INPUT debe ser 'voice')."
                ),
            }
        )
        return
    _listen_requested.set()


def set_trigger_mode(mode):
    """Cambia en caliente el modo de activación de voz. Devuelve el modo final."""
    global _voice_trigger_mode
    mode = (mode or "").lower().strip()
    if mode in ("ptt", "presentation", "auto"):
        _voice_trigger_mode = mode
        if not _is_quiet():
            print(f"[VOZ] Modo de activación -> {mode}")
    return _voice_trigger_mode


def get_trigger_mode():
    """Devuelve el modo de activación de voz actual."""
    return _voice_trigger_mode


def _stdin_ptt_reader():
    """Lee ENTER de la terminal y solicita una escucha (push-to-talk en CLI)."""
    while True:
        try:
            if sys.stdin.readline() == "":
                break  # EOF: terminal cerrada
        except Exception:
            break
        request_listen()


def _wait_for_trigger():
    """Bloquea hasta que toque escuchar, según el modo dinámico actual.

    Devuelve ``True`` si hay que escuchar, ``False`` si hay que reintentar el
    bucle (holograma en pausa o cambio de modo: se reevalúa en la próxima vuelta).
    """
    mode = _voice_trigger_mode

    if mode == "auto":
        return True

    if mode == "presentation":
        # Escuchar de forma continua, pero solo mientras la cámara vea gente.
        # El botón del orbe también puede forzar una escucha puntual.
        while _voice_trigger_mode == "presentation" and not _hologram_paused:
            if _person_present:
                return True
            if _listen_requested.is_set():
                _listen_requested.clear()
                return True
            time.sleep(0.3)
        return False

    # ptt: esperar la solicitud (botón del orbe o ENTER).
    while _voice_trigger_mode == "ptt" and not _hologram_paused:
        if _listen_requested.wait(timeout=0.5):
            _listen_requested.clear()
            return True
    return False


def voice_loop():
    """Voice input loop: microphone → Whisper → LLM → TTS (Regla B: sounddevice)."""
    global _voice_loop_running, ai_busy
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

    # Español fijo + hotwords de data/ (UNEV/Honduras): ver stt/listener.py.
    listener = WhisperListener(language="es")
    # En push-to-talk el visitante ya tocó el botón: dar más margen para empezar
    # a hablar (la UI antes decía "te escucho" antes de abrir el micrófono).
    try:
        ptt_wait = float(os.getenv("WHISPER_PTT_MAX_WAIT_SECONDS", "12") or 12)
        listener.max_wait_seconds = max(listener.max_wait_seconds, ptt_wait)
    except (TypeError, ValueError):
        listener.max_wait_seconds = max(listener.max_wait_seconds, 12.0)

    # Lector de teclado para push-to-talk en CLI (ENTER para hablar). En modo
    # web el disparador llega por WebSocket, así que no tocamos stdin.
    if not WEB_MODE and sys.stdin and sys.stdin.isatty():
        threading.Thread(target=_stdin_ptt_reader, daemon=True).start()
        if not _is_quiet():
            print("[PTT] Pulsa ENTER para hablar.")

    if not _is_quiet():
        print("--- UNEV Hologram (Voz) ---")
        print(f"Modo de activación: {_voice_trigger_mode}")
        print("Habla al micrófono. Di 'salir' o 'exit' para terminar.")
    print(get_stt_status())
    print(get_backend_status())
    print(
        "Ollama recomendado para este equipo: gemma3:1b (el mas rapido en CPU; modelos mayores hacen timeout)."
    )

    # Pre-load the Whisper model so the first utterance is fast
    if not _is_quiet():
        print("[STT] Preparando modelo de voz...")
    listener._load_model()
    # Precargar Piper para no pagar el cold-start en la 1.ª respuesta.
    if not _is_quiet():
        print("[TTS] Preparando motor de voz...")
    warm_tts()

    ai_busy = True
    _voice_loop_running = True
    try:
        while True:
            if _hologram_paused:
                time.sleep(0.5)
                continue

            # Esperar el disparador de activación según el modo actual (ptt /
            # presentation / auto). Bloquea hasta que el botón/ENTER soliciten
            # escuchar, o (en presentación) hasta que la cámara vea gente.
            hologram.set_state("idle")
            if not _wait_for_trigger():
                continue

            if not _is_quiet():
                print("\n[STT] Esperando tu voz...")

            # Avisar a la UI: el botón ya se procesó; el mic aún no abre (TTS/eco).
            _emit_voice_event(
                {
                    "type": "status",
                    "status": "listen_arming",
                    "message": "Activando micrófono… habla en un momento",
                }
            )

            # Esperar a que el TTS termine de hablar antes de escuchar al micrófono
            speak_lock.acquire()
            speak_lock.release()
            # Pequeña pausa para que el eco de las bocinas se disipe
            time.sleep(0.5)

            ai_busy = False  # El holograma está libre justo cuando empieza a escuchar
            turn_orchestrator = _get_hologram_turn_orchestrator()
            if turn_orchestrator is not None:
                turn_orchestrator.mark_listening()
            else:
                hologram.set_state("listening")
            # Solo ahora el micrófono está abierto: la UI debe mostrar "listening".
            _emit_voice_event({"type": "status", "status": "listening"})
            user_input = listener.listen_once()
            ai_busy = True  # El holograma vuelve a estar ocupado procesando el input

            if not user_input:
                # Sin esto la WebApp se queda en "Te escucho…" para siempre.
                _emit_voice_event(
                    {
                        "type": "status",
                        "status": "listen_idle",
                        "message": "No te escuché. Toca de nuevo para hablar.",
                    }
                )
                continue

            if normalize_text(user_input) in ["quit", "exit", "salir"]:
                if not _is_quiet():
                    print("¡Hasta pronto!")
                break

            try:
                command_response = handle_command(user_input)
                if command_response:
                    speak(command_response)
                    continue

                print("The AI is thinking...")
                hologram.set_state("thinking")
                # Stream LLM + habla por cláusulas (no espera a la respuesta completa).
                ask_ai_and_speak(user_input, CURRENT_MODE)
            finally:
                pass  # ai_busy se controla al inicio del loop
    finally:
        _voice_loop_running = False


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
