#!/usr/bin/env python3
"""Prueba de humo del motor Lightpanda contra el servicio real.

Los tests unitarios usan un doble del socket CDP; este script valida el
protocolo de verdad. Requiere el contenedor arriba:

    docker compose up -d lightpanda
    ./.venv/bin/python scripts/smoke_lightpanda.py [URL]
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.lightpanda_engine import (  # noqa: E402
    LightpandaError,
    _cdp_url,
    fetch_page_text,
)

DEFAULT_URL = "https://example.com"


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    print(f"CDP     : {_cdp_url()}")
    print(f"Objetivo: {url}")

    started = time.monotonic()
    try:
        page = fetch_page_text(url)
    except LightpandaError as error:
        print(f"\nFALLO: {error}")
        print("\n¿Está el servicio arriba?  docker compose up -d lightpanda")
        return 1

    elapsed = time.monotonic() - started
    print(f"\nOK en {elapsed:.2f}s")
    print(f"  título    : {page.title or '(sin título)'}")
    print(f"  url final : {page.url}")
    print(f"  caracteres: {len(page.text)} (recortado={page.truncated})")
    print("\n--- primeros 400 caracteres ---")
    print(page.text[:400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
