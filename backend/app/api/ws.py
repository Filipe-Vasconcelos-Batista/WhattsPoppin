import uuid
from collections import defaultdict
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
MAX_IDS_PER_REQUEST = 500


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
    # Gerado por quem envia: liga os recibos (sent/delivered/read) à mensagem
    # dele, e deixa quem recebe descartar reenvios da mesma mensagem.
    client_message_id: uuid.UUID
    envelopes: list[EnvelopeIn] = Field(max_length=MAX_ENVELOPES)


# O cliente confirma depois de processar - só então a linha sai da fila.
class AckIn(BaseModel):
    type: Literal["ack"]
    message_ids: list[uuid.UUID] = Field(max_length=MAX_IDS_PER_REQUEST)


class ReadReceiptIn(BaseModel):
    device_id: uuid.UUID  # device de quem enviou as mensagens lidas
    client_message_ids: list[uuid.UUID] = Field(max_length=MAX_IDS_PER_REQUEST)


class ReadIn(BaseModel):
    type: Literal["read"]
    conversation_id: uuid.UUID
    receipts: list[ReadReceiptIn] = Field(max_length=MAX_ENVELOPES)


async def _deliver(device_id: uuid.UUID, message_id: uuid.UUID, payload: dict[str, Any]) -> None:
    await connection_manager.send_to_device(device_id, {**payload, "message_id": str(message_id)})


async def _enqueue_and_deliver(device_id: uuid.UUID, payload: dict[str, Any]) -> None:
    # Primeiro para a fila, depois entrega - se o device estiver offline (ou
    # cair antes do ack), recebe ao religar.
    message_id = await run_sync(outbox.enqueue, device_id, payload)
    await _deliver(device_id, message_id, payload)


async def _flush_pending(device_id: uuid.UUID) -> None:
    for message_id, payload in await run_sync(outbox.pending_for, device_id):
        await _deliver(device_id, message_id, payload)


def _receipt(status: str, conversation_id: str, client_message_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "receipt",
        "status": status,
        "conversation_id": conversation_id,
        "client_message_ids": client_message_ids,
    }


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
        await _enqueue_and_deliver(
            envelope.device_id,
            {
                "type": "message",
                "conversation_id": str(message.conversation_id),
                "client_message_id": str(message.client_message_id),
                # Vem da ligação, nunca do que o cliente diz
                "sender_device_id": str(sender_device_id),
                "header": envelope.header.model_dump(),
                "ciphertext": envelope.ciphertext,
                "x3dh": envelope.x3dh.model_dump() if envelope.x3dh else None,
            },
        )

    # Já está na fila: a partir daqui a mensagem não se perde.
    await connection_manager.send_to_device(
        sender_device_id,
        {"type": "sent", "client_message_id": str(message.client_message_id)},
    )


async def _handle_ack(device_id: uuid.UUID, acknowledgement: AckIn) -> None:
    acked = await run_sync(outbox.ack, device_id, acknowledgement.message_ids)

    # Recibo "delivered" para quem enviou cada mensagem confirmada. Só para
    # mensagens - o ack de um recibo não gera outro recibo.
    delivered: dict[tuple[str, str], list[str]] = defaultdict(list)
    for payload in acked:
        client_message_id = payload.get("client_message_id")
        # Linhas antigas (da fila antes dos recibos) não têm client_message_id:
        # não há a quem nem sobre o quê mandar recibo.
        if payload.get("type") != "message" or not client_message_id:
            continue
        key = (payload["sender_device_id"], payload["conversation_id"])
        delivered[key].append(client_message_id)

    for (sender_device_id, conversation_id), client_message_ids in delivered.items():
        await _enqueue_and_deliver(
            uuid.UUID(sender_device_id),
            _receipt("delivered", conversation_id, client_message_ids),
        )


async def _handle_read(reader_device_id: uuid.UUID, read: ReadIn) -> None:
    # Só se pode mandar recibos de leitura a devices da mesma conversa.
    allowed = set(await run_sync(find_recipient_device_ids, read.conversation_id, reader_device_id))
    for receipt in read.receipts:
        if receipt.device_id not in allowed or not receipt.client_message_ids:
            continue
        await _enqueue_and_deliver(
            receipt.device_id,
            _receipt(
                "read",
                str(read.conversation_id),
                [str(client_message_id) for client_message_id in receipt.client_message_ids],
            ),
        )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, device_id: uuid.UUID) -> None:
    await websocket.accept()
    connection_manager.register(device_id, websocket)

    try:
        await run_sync(outbox.purge_expired)
        await _flush_pending(device_id)

        while True:
            data = await websocket.receive_json()
            kind = data.get("type") if isinstance(data, dict) else None
            try:
                if kind == "ack":
                    await _handle_ack(device_id, AckIn.model_validate(data))
                elif kind == "read":
                    await _handle_read(device_id, ReadIn.model_validate(data))
                else:
                    await _handle_message(device_id, OutgoingMessage.model_validate(data))
            except ValidationError:
                continue
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.unregister(device_id, websocket)
