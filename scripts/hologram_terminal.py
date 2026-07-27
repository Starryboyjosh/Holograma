#!/usr/bin/env python3
"""Control manual del holograma desde la terminal.

Ejemplos:
    python scripts/hologram_terminal.py --ip 10.10.2.212
    python scripts/hologram_terminal.py --ip 10.10.2.212 --ip 10.10.2.213

Comandos dentro del programa:
    v N       reproducir el video N de la playlist
    n         siguiente video
    b         video anterior
    s         iniciar / RUN
    p         pausar
    r         reanudar
    q         salir y desconectar
"""

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from hologram_controller import HologramFanController  # noqa: E402


def send_to_all(fans: list[tuple[str, HologramFanController]], action: str) -> None:
    for ip, fan in fans:
        try:
            getattr(fan, action)()
            print(f"[OK] {ip}: {action}")
        except (ConnectionError, OSError, ValueError) as error:
            print(f"[FAIL] {ip}: {error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ip", action="append", required=True, help="IP del holograma; se puede repetir")
    parser.add_argument("--port", type=int, default=50200)
    args = parser.parse_args()

    fans: list[tuple[str, HologramFanController]] = []
    for ip in args.ip:
        fan = HologramFanController(ip=ip, port=args.port, verbose=True)
        try:
            fan.connect()
            fans.append((ip, fan))
        except (ConnectionError, OSError) as error:
            print(f"[FAIL] {ip}: {error}")

    if not fans:
        print("No se pudo conectar a ningún holograma.")
        return 1

    print("\nComandos: v N | n | b | s | p | r | q")
    try:
        while True:
            try:
                command = input("holograma> ").strip().lower()
            except EOFError:
                break
            if command == "q":
                break
            if command.startswith("v "):
                try:
                    index = int(command.split(maxsplit=1)[1])
                    for ip, fan in fans:
                        try:
                            fan.play_file(index)
                            print(f"[OK] {ip}: clip {index}")
                        except (ConnectionError, OSError, ValueError) as error:
                            print(f"[FAIL] {ip}: clip {index}: {error}")
                except ValueError:
                    print("Uso: v N, por ejemplo: v 2")
                continue
            actions = {"n": "next_file", "b": "prev_file", "s": "start", "p": "pause", "r": "play"}
            if command in actions:
                send_to_all(fans, actions[command])
                continue
            print("Comando inválido. Usa: v N | n | b | s | p | r | q")
    finally:
        for _ip, fan in fans:
            fan.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
