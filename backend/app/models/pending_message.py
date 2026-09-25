import uuid
from datetime import UTC, datetime

import peewee as pw

from app.models.base import BaseModel
from app.models.device import Device


# Envelope cifrado à espera de ser confirmado (ack) pelo device destinatário -
# uma linha por device, apagada quando ele confirma. O servidor nunca
# interpreta `payload`: é o envelope opaco (header, ciphertext, x3dh).
class PendingMessage(BaseModel):
    id = pw.UUIDField(primary_key=True, default=uuid.uuid4)  # = message_id
    recipient_device = pw.ForeignKeyField(Device, on_delete="CASCADE")
    payload = pw.TextField()
    created_at = pw.DateTimeField(default=lambda: datetime.now(UTC), index=True)

    class Meta:
        table_name = "pending_messages"
        indexes = ((("recipient_device", "created_at"), False),)
