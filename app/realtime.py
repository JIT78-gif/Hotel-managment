import asyncio
from collections import defaultdict
from typing import Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._channels: Dict[int, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, cafe_id: int, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._channels[cafe_id].add(ws)

    async def disconnect(self, cafe_id: int, ws: WebSocket) -> None:
        async with self._lock:
            self._channels[cafe_id].discard(ws)

    async def broadcast(self, cafe_id: int, payload: dict) -> None:
        async with self._lock:
            sockets = list(self._channels.get(cafe_id, ()))
        dead = []
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._channels[cafe_id].discard(ws)


manager = ConnectionManager()
