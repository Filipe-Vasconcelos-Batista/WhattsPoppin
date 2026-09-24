import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db.sync import run_sync
from app.services.connections import connection_manager
from app.services.messaging import find_recipient_device_ids

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, device_id: uuid.UUID) -> None:
    await websocket.accept()
    connection_manager.register(device_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            conversation_id = uuid.UUID(data["conversation_id"])
            text = data["text"]

            recipient_device_ids = await run_sync(
                find_recipient_device_ids, conversation_id, device_id
            )
            for recipient_id in recipient_device_ids:
                await connection_manager.send_to_device(
                    recipient_id,
                    {"type": "message", "conversation_id": str(conversation_id), "text": text},
                )
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.unregister(device_id)
