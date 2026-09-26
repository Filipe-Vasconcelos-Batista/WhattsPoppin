import uuid
from dataclasses import dataclass

from app.models import User
from app.services.conversations import find_conversation


@dataclass
class UserSummary:
    user_id: uuid.UUID
    display_name: str
    # A conversa 1:1 com este utilizador, se já existir - deixa o cliente ligar
    # as mensagens guardadas (por conversa) à entrada certa da lista (por user).
    conversation_id: uuid.UUID | None = None


def list_other_users(exclude_user_id: uuid.UUID) -> list[UserSummary]:
    users = User.select().where(User.id != exclude_user_id).order_by(User.created_at)
    return [
        UserSummary(
            user_id=user.id,
            display_name=user.display_name,
            conversation_id=find_conversation(exclude_user_id, user.id),
        )
        for user in users
    ]
