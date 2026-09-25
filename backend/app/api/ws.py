import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

from app.db.sync import run_sync
from app.services.connections import connection_manager
from app.services.messaging import find_recipient_device_ids

router = APIRouter()


# O servidor nunca decifra nada - estes modelos só validam a forma do que
# passa, para um payload mal formado não derrubar a ligação.
class RatchetHeaderIn(BaseModel):
    dh: str  # base64
    pn: int
    n: int


class X3dhPreludeIn(BaseModel):
    identity_key: str  # base64
    ephemeral_key: str  # base64
    signed_prekey_id: int
    one_time_prekey_id: int | None


class EnvelopeIn(BaseModel):
    device_id: uuid.UUID
    header: RatchetHeaderIn
    ciphertext: str  # base64
    x3dh: X3dhPreludeIn | None = None


class OutgoingMessage(BaseModel):
    conversation_id: uuid.UUID
    envelopes: list[EnvelopeIn]


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, device_id: uuid.UUID) -> None:
    await websocket.accept()
    connection_manager.register(device_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            try:
                message = OutgoingMessage.model_validate(data)
            except ValidationError:
                continue

            # Cada envelope só segue para o device indicado, e só se esse
            # device for mesmo participante da conversa - o socket não pode
            # servir para mandar mensagens a quem não está nela.
            allowed = set(
                await run_sync(find_recipient_device_ids, message.conversation_id, device_id)
            )
            for envelope in message.envelopes:
                if envelope.device_id not in allowed:
                    continue
                await connection_manager.send_to_device(
                    envelope.device_id,
                    {
                        "type": "message",
                        "conversation_id": str(message.conversation_id),
                        # Vem da ligação, nunca do que o cliente diz
                        "sender_device_id": str(device_id),
                        "header": envelope.header.model_dump(),
                        "ciphertext": envelope.ciphertext,
                        "x3dh": envelope.x3dh.model_dump() if envelope.x3dh else None,
                    },
                )
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.unregister(device_id)
