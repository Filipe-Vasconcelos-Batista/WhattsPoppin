import uuid

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._active: dict[uuid.UUID, WebSocket] = {}

    def register(self, device_id: uuid.UUID, websocket: WebSocket) -> None:
        self._active[device_id] = websocket

    def unregister(self, device_id: uuid.UUID, websocket: WebSocket | None = None) -> None:
        if websocket is not None and self._active.get(device_id) is not websocket:
            return
        self._active.pop(device_id, None)

    async def send_to_device(self, device_id: uuid.UUID, payload: dict[str, object]) -> bool:
        websocket = self._active.get(device_id)
        if websocket is None:
            return False
        try:
            await websocket.send_json(payload)
        except Exception:
            # Socket já fechado do outro lado - não pode rebentar o handler de
            # quem enviou. As mensagens ficam na fila e seguem ao religar.
            self.unregister(device_id, websocket)
            return False
        return True

    async def broadcast(self, payload: dict[str, object], exclude: uuid.UUID | None = None) -> None:
        for device_id, websocket in list(self._active.items()):
            if device_id == exclude:
                continue
            await websocket.send_json(payload)


connection_manager = ConnectionManager()
