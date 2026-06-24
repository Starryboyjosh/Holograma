#!/usr/bin/env python3
"""
Local diagnostics for camera, audio, STT, TTS, YOLO, and safe face analysis.

Examples:
    python diagnose_hologram.py
    python diagnose_hologram.py --camera --yolo --faces
    python diagnose_hologram.py --speak "Hola, prueba de audio."
"""

import argparse
import importlib
import os
import platform
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")


def ok(message):
    print(f"[OK] {message}")


def warn(message):
    print(f"[WARN] {message}")


def fail(message):
    print(f"[FAIL] {message}")


def check_import(module_name, package_hint=None):
    try:
        module = importlib.import_module(module_name)
    except Exception as error:
        fail(f"{module_name}: {error}")
        if package_hint:
            print(f"       instala: {package_hint}")
        return False

    version = getattr(module, "__version__", "")
    suffix = f" {version}" if version else ""
    ok(f"{module_name}{suffix}")
    return True


def check_environment():
    print("== Sistema ==")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Base: {BASE_DIR}")

    print("\n== Variables clave ==")
    for key in [
        "LLM_PROVIDER",
        "LLM_BACKEND",
        "LLM_MODEL",
        "HOLOGRAM_INPUT",
        "HOLOGRAM_CAMERA",
        "HOLOGRAM_CAMERA_INDEX",
        "HOLOGRAM_FACE_ANALYSIS",
        "YOLO_MODEL",
        "WHISPER_MODEL",
        "WHISPER_DEVICE",
        "TTS_BACKEND",
        "PIPER_MODEL_PATH",
    ]:
        value = os.getenv(key, "")
        if key.endswith("API_KEY") and value:
            value = "***"
        print(f"{key}={value}")


def check_dependencies():
    print("\n== Dependencias Python ==")
    checks = [
        ("dotenv", "python-dotenv"),
        ("numpy", "numpy"),
        ("cv2", "opencv-python"),
        ("ultralytics", "ultralytics"),
        ("sounddevice", "sounddevice"),
        ("faster_whisper", "faster-whisper"),
        ("openai", "openai"),
        ("anthropic", "anthropic"),
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
    ]
    return all(check_import(module, hint) for module, hint in checks)


def check_audio_devices():
    print("\n== Audio Linux/Windows ==")
    try:
        import sounddevice as sd
        devices = sd.query_devices()
    except Exception as error:
        fail(f"No pude consultar dispositivos de audio: {error}")
        return False

    input_count = 0
    output_count = 0
    for index, device in enumerate(devices):
        in_channels = device.get("max_input_channels", 0)
        out_channels = device.get("max_output_channels", 0)
        if in_channels > 0:
            input_count += 1
        if out_channels > 0:
            output_count += 1
        marker = []
        if in_channels > 0:
            marker.append("in")
        if out_channels > 0:
            marker.append("out")
        if marker:
            print(f"{index}: {device.get('name')} ({'/'.join(marker)})")

    if input_count:
        ok(f"{input_count} entrada(s) de audio detectada(s)")
    else:
        fail("No hay micrófono visible para sounddevice")

    if output_count:
        ok(f"{output_count} salida(s) de audio detectada(s)")
    else:
        fail("No hay salida de audio visible para sounddevice")

    return input_count > 0 and output_count > 0


def test_speak(text):
    print("\n== TTS ==")
    try:
        from call import speak
        speak(text)
        ok("Prueba de voz enviada")
        return True
    except Exception as error:
        fail(f"Error en TTS: {error}")
        return False


def test_camera(index):
    print("\n== Cámara ==")
    try:
        from vision.camera import Camera
        with Camera(source=index, width=640, height=480) as camera:
            frame = camera.read_frame()
    except Exception as error:
        fail(f"No pude abrir cámara {index}: {error}")
        return None

    if frame is None:
        fail("La cámara abrió, pero no entregó frame")
        return None

    ok(f"Frame capturado: {frame.shape[1]}x{frame.shape[0]}")
    return frame


def test_yolo(frame):
    print("\n== YOLO personas ==")
    try:
        from vision.person_detector import YoloPersonDetector
        detector = YoloPersonDetector().load()
        persons = detector.detect_persons_in_frame(frame)
    except Exception as error:
        fail(f"YOLO falló: {error}")
        return False

    ok(f"Personas detectadas: {len(persons)}")
    for idx, person in enumerate(persons, start=1):
        print(f"  {idx}: confianza={person['confidence']:.2f}, box={person['box']}")
    return True


def test_faces(frame):
    print("\n== Rostros seguros ==")
    try:
        from vision.face_analyzer import FaceAnalyzer
        result = FaceAnalyzer().load().analyze_frame(frame)
    except Exception as error:
        fail(f"Análisis de rostros falló: {error}")
        return False

    ok(result["description"])
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", action="store_true", help="captura un frame")
    parser.add_argument("--yolo", action="store_true", help="detecta personas en un frame")
    parser.add_argument("--faces", action="store_true", help="cuenta rostros visibles")
    parser.add_argument("--camera-index", type=int, default=int(os.getenv("HOLOGRAM_CAMERA_INDEX", "0")))
    parser.add_argument("--speak", nargs="?", const="Hola, esta es una prueba de audio del holograma.")
    args = parser.parse_args()

    check_environment()
    check_dependencies()
    check_audio_devices()

    if args.speak:
        test_speak(args.speak)

    frame = None
    if args.camera or args.yolo or args.faces:
        frame = test_camera(args.camera_index)

    if frame is not None and args.yolo:
        test_yolo(frame)

    if frame is not None and args.faces:
        test_faces(frame)


if __name__ == "__main__":
    main()
