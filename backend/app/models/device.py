import uuid
from datetime import UTC, datetime

import peewee as pw

from app.models.base import BaseModel
from app.models.user import User


class Device(BaseModel):
    id = pw.UUIDField(primary_key=True, default=uuid.uuid4)
    user = pw.ForeignKeyField(User, backref="devices", on_delete="CASCADE")
    name = pw.CharField(max_length=80, null=True)
    is_active = pw.BooleanField(default=True)
    registered_at = pw.DateTimeField(default=lambda: datetime.now(UTC))
    last_seen_at = pw.DateTimeField(null=True)

    class Meta:
        table_name = "devices"
