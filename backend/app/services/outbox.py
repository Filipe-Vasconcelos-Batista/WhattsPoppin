import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.models import PendingMessage

# Mensagens que nenhum ack confirmou em 30 dias (ex.: device que nunca mais
# se ligou) são descartadas.
PENDING_TTL = timedelta(days=30)


def enqueue(recipient_device_id: uuid.UUID, payload: dict[str, Any]) -> uuid.UUID:
    row = PendingMessage.create(recipient_device=recipient_device_id, payload=json.dumps(payload))
    message_id: uuid.UUID = row.id
    return message_id


def pending_for(device_id: uuid.UUID) -> list[tuple[uuid.UUID, dict[str, Any]]]:
    rows = (
        PendingMessage.select()
        .where(PendingMessage.recipient_device == device_id)
        .order_by(PendingMessage.created_at)
    )
    return [(row.id, json.loads(row.payload)) for row in rows]


# Só apaga linhas do próprio device - um device não pode confirmar (e assim
# apagar) mensagens destinadas a outro.
def ack(device_id: uuid.UUID, message_ids: list[uuid.UUID]) -> int:
    if not message_ids:
        return 0
    deleted: int = (
        PendingMessage.delete()  # type: ignore[misc]  # stubs do peewee
        .where(
            PendingMessage.recipient_device == device_id,
            PendingMessage.id.in_(message_ids),
        )
        .execute()
    )
    return deleted


def purge_expired() -> int:
    cutoff = datetime.now(UTC) - PENDING_TTL
    deleted: int = (
        PendingMessage.delete()  # type: ignore[misc]  # stubs do peewee
        .where(PendingMessage.created_at < cutoff)
        .execute()
    )
    return deleted
