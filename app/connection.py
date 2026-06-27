"""Emisor único de eventos hacia los clientes WebSocket.

El `main.py` actual mezcla dos mecanismos para hablarle al frontend:
`send_to_web_client` (que hace `asyncio.run_coroutine_threadsafe` desde hilos) y
emisiones directas dentro del endpoint async. Esa mezcla de envío *diferido* e
*inmediato* es la causa de las carreras de orden de eventos (síntoma B). Este
`ConnectionManager` centraliza el envío en una sola superficie **async**: nada de
`run_coroutine_threadsafe`, un solo lugar que serializa los mensajes y descarta
los sockets muertos.
"""

import asyncio
from typing import Protocol


class WebSocketLike(Protocol):
    """Lo único que el manager necesita de un WebSocket (FastAPI lo cumple)."""

    async def send_json(self, data: dict) -> None: ...


class ConnectionManager:
    """Registro de conexiones + difusión async, seguro ante sockets caídos."""

    def __init__(self) -> None:
        self._connections: set[WebSocketLike] = set()
        self._lock = asyncio.Lock()

    @property
    def count(self) -> int:
        return len(self._connections)

    async def register(self, websocket: WebSocketLike) -> None:
        async with self._lock:
            self._connections.add(websocket)

    async def unregister(self, websocket: WebSocketLike) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        """Envía *message* a todas las conexiones; descarta las que fallen.

        Se toma una instantánea bajo el lock y el envío ocurre fuera de él, para no
        retener el lock durante I/O de red.
        """
        async with self._lock:
            targets = list(self._connections)

        dead: list[WebSocketLike] = []
        for websocket in targets:
            try:
                await websocket.send_json(message)
            except Exception:
                # El cliente se fue o el socket está roto: lo marcamos para purgar.
                dead.append(websocket)

        if dead:
            async with self._lock:
                for websocket in dead:
                    self._connections.discard(websocket)
