from datetime import UTC, datetime

import peewee as pw

from app.models.base import BaseModel
from app.models.user import User

PENDING_OUTGOING = "pending_outgoing"
PENDING_INCOMING = "pending_incoming"
ACCEPTED = "accepted"


class Contact(BaseModel):
    owner = pw.ForeignKeyField(User, backref="contacts", on_delete="CASCADE")
    contact = pw.ForeignKeyField(User, backref="contact_of", on_delete="CASCADE")
    status = pw.CharField(max_length=16)
    created_at = pw.DateTimeField(default=lambda: datetime.now(UTC))
    updated_at = pw.DateTimeField(default=lambda: datetime.now(UTC))

    class Meta:
        table_name = "contacts"
        primary_key = pw.CompositeKey("owner", "contact")
