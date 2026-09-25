import uuid
from typing import Any, Literal

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError

from app.db.sync import run_sync
from app.services import outbox
from app.services.connections import connection_manager
from app.services.messaging import find_recipient_device_ids

router = APIRouter()

MAX_CIPHERTEXT_LENGTH = 64 * 1024  # base64
MAX_ENVELOPES = 50
MAX_ACK_IDS = 500


# O servidor nunca decifra nada - estes modelos só validam a forma do que
# passa, para um payload mal formado não derrubar a ligação.
class RatchetHeaderIn(BaseModel):
    dh: str = Field(max_length=64)  # base64
    pn: int
    n: int


class X3dhPreludeIn(BaseModel):
    identity_key: str = Field(max_length=64)  # base64
    ephemeral_key: str = Field(max_length=64)  # base64
    signed_prekey_id: int
    one_time_prekey_id: int | None


class EnvelopeIn(BaseModel):
    device_id: uuid.UUID
    header: RatchetHeaderIn
    ciphertext: str = Field(max_length=MAX_CIPHERTEXT_LENGTH)  # base64
    x3dh: X3dhPreludeIn | None = None


class OutgoingMessage(BaseModel):
    conversation_id: uuid.UUID
    envelopes: list[EnvelopeIn] = Field(max_length=MAX_ENVELOPES)


# O cliente confirma depois de processar - só então a linha sai da fila.
class AckIn(BaseModel):
    type: Literal["ack"]
    message_ids: list[uuid.UUID] = Field(max_length=MAX_ACK_IDS)


async def _deliver(device_id: uuid.UUID, message_id: uuid.UUID, payload: dict[str, Any]) -> None:
    await connection_manager.send_to_device(device_id, {**payload, "message_id": str(message_id)})


async def _flush_pending(device_id: uuid.UUID) -> None:
    for message_id, payload in await run_sync(outbox.pending_for, device_id):
        await _deliver(device_id, message_id, payload)


async def _handle_message(sender_device_id: uuid.UUID, message: OutgoingMessage) -> None:
    # Cada envelope só segue para o device indicado, e só se esse device for
    # mesmo participante da conversa - o socket não pode servir para mandar
    # mensagens a quem não está nela.
    allowed = set(
        await run_sync(find_recipient_device_ids, message.conversation_id, sender_device_id)
    )
    for envelope in message.envelopes:
        if envelope.device_id not in allowed:
            continue
        payload: dict[str, Any] = {
            "type": "message",
            "conversation_id": str(message.conversation_id),
            # Vem da ligação, nunca do que o cliente diz
            "sender_device_id": str(sender_device_id),
            "header": envelope.header.model_dump(),
            "ciphertext": envelope.ciphertext,
            "x3dh": envelope.x3dh.model_dump() if envelope.x3dh else None,
        }
        # Primeiro para a fila, depois entrega - se o device estiver offline
        # (ou cair antes do ack), recebe ao religar.
        message_id = await run_sync(outbox.enqueue, envelope.device_id, payload)
        await _deliver(envelope.device_id, message_id, payload)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, device_id: uuid.UUID) -> None:
    await websocket.accept()
    connection_manager.register(device_id, websocket)

    try:
        await run_sync(outbox.purge_expired)
        await _flush_pending(device_id)

        while True:
            data = await websocket.receive_json()
            try:
                if isinstance(data, dict) and data.get("type") == "ack":
                    acknowledgement = AckIn.model_validate(data)
                    await run_sync(outbox.ack, device_id, acknowledgement.message_ids)
                else:
                    await _handle_message(device_id, OutgoingMessage.model_validate(data))
            except ValidationError:
                continue
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.unregister(device_id, websocket)
