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
import json
import os
import platform
import sys
import time
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
    print("\n== YOLOE (personas + open-vocab) ==")
    try:
        from vision.person_detector import DEFAULT_YOLOE_WEIGHTS, YoloPersonDetector

        detector = YoloPersonDetector().load()
        info = detector.model_info()
        analysis = detector.analyze_frame(frame)
    except Exception as error:
        fail(f"YOLOE falló: {error}")
        return False

    ok(
        f"Modelo {info.get('weights')} (canónico={DEFAULT_YOLOE_WEIGHTS}) "
        f"backend={info.get('backend')} set_classes={info.get('has_set_classes')}"
    )
    ok(f"Prompts: {info.get('active_prompts')}")
    ok(f"Personas: {analysis.get('person_count', 0)}")
    for idx, person in enumerate(analysis.get("persons") or [], start=1):
        print(f"  P{idx}: conf={person['confidence']:.2f}, box={person['box']}")
    customs = analysis.get("custom_objects") or []
    ok(f"Custom open-vocab: {len(customs)}")
    for idx, obj in enumerate(customs, start=1):
        print(
            f"  C{idx}: {obj.get('label')} conf={obj['confidence']:.2f} "
            f"src={obj.get('source', 'yoloe')}"
        )
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


def hologram_config_path() -> Path:
    return BASE_DIR / "data" / "hologram_media.json"


def diagnose_hologram(
    config_only: bool, simulate: bool, role: str | None, index: int | None, connect: bool,
    manager_factory=None, connect_timeout: float = 1.0, now_fn=time.monotonic, sleep_fn=time.sleep,
) -> int:
    """Inspect the three independent fans without implying playback confirmation."""
    from app.hologram.config_store import HologramConfigStore
    from app.hologram.models import HologramConfig
    from app.hologram.simulator import HologramSimulator

    path = hologram_config_path()
    if path.exists():
        try:
            with path.open(encoding="utf-8") as handle:
                config = HologramConfig.from_dict(json.load(handle))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            fail("Archivo de configuración corrupto; se conservaron fallback y backup sin modificar.")
            return 1
        ok("Archivo de configuración original válido.")
    else:
        config = HologramConfigStore(path).load()
        warn("Archivo de configuración inexistente; se usa catálogo seguro en memoria.")
    print("== Holograma: catálogo lógico (hardware write-only) ==")
    for unit_role, unit in config.units.items():
        print(f"{unit_role}: ip={unit.ip or '-'} port={unit.port} enabled={unit.enabled} identify_index={unit.identify_index}")
    print("mascota:", ", ".join(f"{name}={value}" for name, value in config.mascot_states.items()))
    print("identidades:", ", ".join(f"{item.id}={item.index}" for item in config.identities))
    print("promociones:", ", ".join(f"{item.id}={item.index}" for item in config.promotions) or "(ninguna)")
    if role is not None and role not in config.units:
        fail("role debe ser top, center o bottom")
        return 2
    if index is not None and not 0 <= index <= 255:
        fail("index debe estar entre 0 y 255")
        return 2
    if config_only:
        return 0
    target_role = role or "top"
    if simulate:
        simulator = HologramSimulator({key: value.ip or f"sim-{key}" for key, value in config.units.items()})
        simulator.connect(target_role)
        if index is not None:
            simulator.play(target_role, index, semantic_id="diagnostic")
        for event in simulator.get_events():
            print(event)
        simulator.close()
        return 0
    if not connect:
        warn("No se envió hardware. Usa --simulate o --connect explícitamente.")
        return 0
    from app.hologram.unit_manager import HologramUnitManager

    unit = config.units[target_role]
    if not unit.enabled or not unit.ip:
        fail(f"{target_role} no tiene una IP habilitada")
        return 2
    print(f"Hardware: role={target_role} ip={unit.ip} port={unit.port} index={index if index is not None else '-'}")
    manager = (manager_factory or HologramUnitManager)(target_role, unit)
    try:
        manager.start()
        deadline = now_fn() + max(0.0, connect_timeout)
        while not manager.status().connected and now_fn() < deadline:
            sleep_fn(0.02)
        if not manager.status().connected:
            fail("No fue posible establecer conexión.")
            return 1
        ok("Conexión establecida.")
        if index is not None:
            manager.execute_legacy("play_file", index)
            ok(f"Comando de índice {index} enviado sin excepción; reproducción visual no confirmada.")
        else:
            ok("Conexión establecida; no se envió índice.")
    except Exception as error:
        fail(f"Operación de hardware falló: {error}")
        return 1
    finally:
        manager.close()
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", action="store_true", help="captura un frame")
    parser.add_argument(
        "--yolo",
        action="store_true",
        help="detecta personas + custom con YOLOE (yoloe-26n-seg)",
    )
    parser.add_argument("--faces", action="store_true", help="cuenta rostros visibles")
    parser.add_argument("--camera-index", type=int, default=int(os.getenv("HOLOGRAM_CAMERA_INDEX", "0")))
    parser.add_argument("--speak", nargs="?", const="Hola, esta es una prueba de audio del holograma.")
    parser.add_argument("--config-only", action="store_true", help="valida e imprime el catálogo de tres ventiladores")
    parser.add_argument("--simulate", action="store_true", help="simula una conexión/índice sin hardware")
    parser.add_argument("--role", choices=("top", "center", "bottom"), help="unidad objetivo para diagnóstico")
    parser.add_argument("--index", type=int, help="índice físico 0..255; 0 es válido")
    parser.add_argument("--connect", action="store_true", help="permite conexión de hardware explícita")
    args = parser.parse_args()

    if args.config_only or args.simulate or args.role or args.index is not None or args.connect:
        raise SystemExit(diagnose_hologram(args.config_only, args.simulate, args.role, args.index, args.connect))

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
