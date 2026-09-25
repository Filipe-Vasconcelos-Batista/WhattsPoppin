import uuid
from datetime import UTC, datetime

import peewee as pw

from app.models.base import BaseModel


class User(BaseModel):
    id = pw.UUIDField(primary_key=True, default=uuid.uuid4)
    username = pw.CharField(max_length=32, unique=True)
    password_hash = pw.CharField(max_length=100)
    display_name = pw.CharField(max_length=80)
    created_at = pw.DateTimeField(default=lambda: datetime.now(UTC))

    class Meta:
        table_name = "users"
