from datetime import UTC, datetime

import peewee as pw

from app.models.base import BaseModel

TRUSTED = "trusted"
PENDING = "pending"
BLOCKED = "blocked"
class FederatedServer(BaseModel):
    domain = pw.CharField(max_length=255, primary_key=True)
    key_id = pw.CharField(max_length=32)
    verify_key = pw.CharField(max_length=64)  # Ed25519 público, base64
    trust_status = pw.CharField(max_length=16, default=TRUSTED)
    first_seen_at = pw.DateTimeField(default=lambda: datetime.now(UTC))
    last_seen_at = pw.DateTimeField(default=lambda: datetime.now(UTC))
    changed_key = pw.CharField(max_length=64, null=True)
    key_changed_at = pw.DateTimeField(null=True)

    class Meta:
        table_name = "federated_servers"
