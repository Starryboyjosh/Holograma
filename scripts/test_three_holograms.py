#!/usr/bin/env python3
"""Prueba un video distinto en cada holograma conectado a la red.

Ejemplo:
    python scripts/test_three_holograms.py \
        --hologram 192.168.1.101:0 \
        --hologram 192.168.1.102:1 \
        --hologram 192.168.1.103:2

El índice es la posición del archivo en la playlist del holograma, no el
nombre del MP4. La prueba envía RUN y luego el comando play_file(index).
"""

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from hologram_controller import HologramArrayTester  # noqa: E402


def parse_assignment(value: str) -> tuple[str, int]:
    ip, separator, raw_index = value.rpartition(":")
    if not separator or not ip.strip():
        raise argparse.ArgumentTypeError("usa el formato IP:índice, por ejemplo 192.168.1.101:0")
    try:
        index = int(raw_index)
    except ValueError as error:
        raise argparse.ArgumentTypeError("el índice debe ser un entero entre 0 y 255") from error
    if not 0 <= index <= 255:
        raise argparse.ArgumentTypeError("el índice debe estar entre 0 y 255")
    return ip.strip(), index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hologram",
        action="append",
        required=True,
        type=parse_assignment,
        metavar="IP:ÍNDICE",
        help="asignación repetible; usa tres para probar tres unidades",
    )
    parser.add_argument("--port", type=int, default=50200, help="puerto TCP (default: 50200)")
    parser.add_argument(
        "--gap",
        type=float,
        default=0.25,
        help="segundos entre RUN y PLAY FILE (default: 0.25)",
    )
    args = parser.parse_args()

    if len(args.hologram) != 3:
        parser.error("esta prueba requiere exactamente tres opciones --hologram")

    print("== Prueba de tres hologramas ==")
    ips = [ip for ip, _index in args.hologram]
    if len(set(ips)) != len(ips):
        print("[WARN] Hay IPs repetidas: los índices se enviarán al mismo dispositivo.")
        print("       Para videos simultáneos distintos se necesitan tres IPs diferentes.")
    for position, (ip, index) in enumerate(args.hologram, start=1):
        print(f"{position}. {ip}:{args.port} -> clip {index}")

    results = HologramArrayTester(args.hologram, port=args.port, command_gap=args.gap).run()
    failed = 0
    for result in results:
        if result["status"] == "ok":
            print(f"[OK] {result['ip']} reproduciendo clip {result['index']}")
        else:
            failed += 1
            print(f"[FAIL] {result['ip']} clip {result['index']}: {result['message']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
