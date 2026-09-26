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


MAX_DISPLAY_NAME_LENGTH = 80


class DisplayNameError(Exception):
    pass


def update_display_name(user_id: uuid.UUID, display_name: str) -> str:
    display_name = display_name.strip()
    if not display_name:
        raise DisplayNameError("O nome de exibição não pode ficar vazio")
    if len(display_name) > MAX_DISPLAY_NAME_LENGTH:
        raise DisplayNameError(
            f"O nome de exibição tem no máximo {MAX_DISPLAY_NAME_LENGTH} caracteres"
        )

    User.update(display_name=display_name).where(User.id == user_id).execute()
    return display_name


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
