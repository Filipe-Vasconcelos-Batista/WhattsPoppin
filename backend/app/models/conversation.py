import uuid
from datetime import UTC, datetime

import peewee as pw

from app.models.base import BaseModel
from app.models.user import User


class Conversation(BaseModel):
    id = pw.UUIDField(primary_key=True, default=uuid.uuid4)
    is_group = pw.BooleanField(default=False)
    created_at = pw.DateTimeField(default=lambda: datetime.now(UTC))

    class Meta:
        table_name = "conversations"


class ConversationParticipant(BaseModel):
    conversation = pw.ForeignKeyField(Conversation, backref="participants", on_delete="CASCADE")
    user = pw.ForeignKeyField(User, on_delete="CASCADE")
    joined_at = pw.DateTimeField(default=lambda: datetime.now(UTC))

    class Meta:
        table_name = "conversation_participants"
        primary_key = pw.CompositeKey("conversation", "user")
