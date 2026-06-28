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
        # Loop del servidor, capturado en el arranque vía bind_loop(). Lo necesitan
        # los productores en hilos (voz/cámara) para saltar del hilo al event loop.
        # Antes esto vivía como el global `running_loop` en main.py; ahora el dueño
        # del registro de sockets también es dueño del puente hilo→loop.
        self._loop: asyncio.AbstractEventLoop | None = None

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

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Captura el event loop del servidor para emitir desde hilos no-async.

        Se llama una vez en el arranque (lifespan). Es la contraparte de
        `broadcast_threadsafe`: sin un loop enlazado, los hilos no tienen a dónde
        encolar.
        """
        self._loop = loop

    def broadcast_threadsafe(self, message: dict) -> None:
        """Difunde *message* desde un hilo (voz/cámara) hacia el event loop.

        Los productores de voz/cámara son hilos reales: no pueden `await`. Esto
        encola `broadcast` en el loop con `run_coroutine_threadsafe` —el puente
        hilo→loop imprescindible. Si el loop aún no está enlazado (arranque
        incompleto o test), se descarta en silencio en vez de reventar el hilo.
        """
        loop = self._loop
        if loop is None:
            return
        asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)

    async def close_all(self) -> None:
        """Cierra y olvida todas las conexiones (apagado ordenado del servidor).

        El manager es ahora el dueño del registro de sockets, así que también es
        responsable de cerrarlos limpiamente al apagar. `close()` es opcional en el
        protocolo (FastAPI lo cumple); si no existe o falla, se ignora.
        """
        async with self._lock:
            targets = list(self._connections)
            self._connections.clear()

        for websocket in targets:
            close = getattr(websocket, "close", None)
            if close is None:
                continue
            try:
                await close()
            except Exception:
                pass
