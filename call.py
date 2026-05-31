import base64
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from llm_backend import generate_reply, get_backend_status
from skills.appearance import get_cordial_observation
from skills.event_mode import get_greeting, get_system_prompt
from skills.presence import PresenceManager
from skills.router import route_local_skill
from skills.university import get_university_context, normalize_text

# Fix for Wayland/CachyOS.
os.environ["QT_QPA_PLATFORM"] = "xcb"

CURRENT_MODE = os.getenv("HOLOGRAM_MODE", "normal")
DEFAULT_PIPER_MODEL = "es_ES-sharvard-medium.onnx"
presence_manager = PresenceManager(
    greeting_cooldown_seconds=30, absence_reset_seconds=8
)


def clean_for_tts(text):
    """Remove characters that can sound awkward when read by Piper."""
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
    for old, new in replacements.items():
        clean_text = clean_text.replace(old, new)

    return clean_text.strip()


def get_piper_model_path():
    """Return the Piper voice model to use, preferring Spanish voices."""
    configured_model = os.getenv("PIPER_MODEL_PATH")
    if configured_model:
        return configured_model

    if os.path.exists(DEFAULT_PIPER_MODEL):
        return DEFAULT_PIPER_MODEL

    spanish_models = sorted(Path(".").glob("es_*.onnx"))
    if spanish_models:
        return str(spanish_models[0])

    if os.path.exists(FALLBACK_PIPER_MODEL):
        print(f"AVISO: No encontré una voz en español. Usando {FALLBACK_PIPER_MODEL}.")
        return FALLBACK_PIPER_MODEL

    return DEFAULT_PIPER_MODEL


def get_piper_sample_rate(model_path):
    """Read Piper sample rate from the model JSON sidecar when available."""
    config_path = f"{model_path}.json"

    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        return "22050"
    except json.JSONDecodeError:
        print(f"AVISO: No pude leer {config_path}. Usando 22050 Hz.")
        return "22050"

    sample_rate = config.get("audio", {}).get("sample_rate", 22050)
    return str(sample_rate)


def speak_with_windows_voice(text):
    """Use Windows built-in speech synthesis when Piper/aplay is unavailable."""
    powershell = shutil.which("powershell") or shutil.which("powershell.exe")
    if not powershell:
        print("AVISO: No encontre PowerShell para reproducir voz en Windows.")
        return False

    encoded_text = base64.b64encode(text.encode("utf-8")).decode("ascii")
    script = (
        f"$text = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_text}')); "
        "Add-Type -AssemblyName System.Speech; "
        "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$voices = @($speaker.GetInstalledVoices() | "
        "Where-Object { $_.VoiceInfo.Culture.Name -like 'es-*' }); "
        "if ($voices.Count -gt 0) { "
        "$speaker.SelectVoice($voices[0].VoiceInfo.Name) "
        "}; "
        "$speaker.Volume = 100; "
        "$speaker.Rate = 0; "
        "$speaker.Speak($text); "
        "$speaker.Dispose();"
    )

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
        if result.returncode != 0:
            print(
                "AVISO: No pude reproducir voz en Windows. Revisa el dispositivo de audio."
            )
            return False

        return True
    except Exception as error:
        print(f"Error reproduciendo voz de Windows: {error}")
        return False


def speak(text):
    """Pipes text into the Piper TTS engine and outputs to speakers."""
    clean_text = clean_for_tts(text)

    if not clean_text:
        return

    print(f"\nSpeaking: {clean_text}")

    if platform.system() == "Windows":
        speak_with_windows_voice(clean_text)
        return

    model_path = get_piper_model_path()

    if not os.path.exists(model_path):
        print(
            f"ERROR: No encontré la voz {model_path}. "
            "Descarga una voz de Piper en español o define PIPER_MODEL_PATH."
        )
        return

    config_path = f"{model_path}.json"
    if not os.path.exists(config_path):
        print(
            f"ERROR: Falta {config_path}. "
            "Piper necesita el archivo .onnx y su .onnx.json correspondiente."
        )
        return

    sample_rate = get_piper_sample_rate(model_path)

    try:
        piper_process = subprocess.Popen(
            ["piper", "--model", model_path, "--output_raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        aplay_process = subprocess.Popen(
            ["aplay", "-r", sample_rate, "-f", "S16_LE", "-t", "raw"],
            stdin=piper_process.stdout,
        )

        if piper_process.stdin:
            piper_process.stdin.write((clean_text + "\n").encode("utf-8"))
            piper_process.stdin.close()

        if piper_process.stdout:
            piper_process.stdout.close()

        aplay_process.wait()
        piper_process.wait()
    except FileNotFoundError as error:
        print(f"No se encontró el comando requerido para voz: {error.filename}")
    except Exception as error:
        print(f"Error reproduciendo voz: {error}")


def ask_ai(user_input, mode=None):
    mode = mode or CURRENT_MODE

    local_response = route_local_skill(user_input)
    if local_response:
        return local_response

    return generate_reply(
        user_input=user_input,
        system_prompt=get_system_prompt(mode),
        university_context=get_university_context(),
    )


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
        presence_manager.should_greet(True)
        return get_cordial_observation("grupo")

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


def chat_to_voice():
    print("--- UNEV Hologram Test ---")
    print("Type a message to the AI.")
    print(
        "Commands: 'quit', 'exit', 'ayuda', 'backend', 'saludar', 'persona', 'grupo', 'formal'."
    )
    print("Modes: 'modo jueces', 'modo expo', 'modo admisiones', 'modo normal'.")
    print(get_backend_status())
    print("Ollama recomendado para este setup: qwen3:8b.")

    while True:
        user_input = input("\nYou: ").strip()

        if not user_input:
            continue

        if normalize_text(user_input) in ["quit", "exit", "salir"]:
            break

        command_response = handle_command(user_input)
        if command_response:
            speak(command_response)
            continue

        print("The AI is thinking...")
        reply = ask_ai(user_input, CURRENT_MODE)
        speak(reply)


if __name__ == "__main__":
    chat_to_voice()
