import uuid
from datetime import UTC, datetime

import peewee as pw

from app.models.base import BaseModel
from app.models.user import User


class Device(BaseModel):
    id = pw.UUIDField(primary_key=True, default=uuid.uuid4)
    user = pw.ForeignKeyField(User, backref="devices", on_delete="CASCADE")
    name = pw.CharField(max_length=80, null=True)
    # token guardado no localStorage do cliente para reconhecer o mesmo
    # dispositivo entre sessões - substitui um login real, que ainda não
    # existe (ver por_decidir no projeto-chat-selfhosted.yaml)
    client_token = pw.CharField(max_length=64, unique=True, null=True)
    is_active = pw.BooleanField(default=True)
    registered_at = pw.DateTimeField(default=lambda: datetime.now(UTC))
    last_seen_at = pw.DateTimeField(null=True)
    # Chaves de sessão E2E (X3DH) publicadas pelo dispositivo - ver
    # plano-cifra-ponta-a-ponta.md. identity_key é a chave pública Ed25519
    # (IK); signed_prekey é X25519 (SPK), assinado com a IK
    # (signed_prekey_signature). signed_prekey_id identifica a versão do
    # SPK em uso, para permitir rotação futura.
    identity_key = pw.BlobField(null=True)
    signed_prekey = pw.BlobField(null=True)
    signed_prekey_signature = pw.BlobField(null=True)
    signed_prekey_id = pw.IntegerField(null=True)

    class Meta:
        table_name = "devices"
