import uuid
from dataclasses import dataclass

from app.models import User
from app.services.conversations import find_conversation
from app.services.identifiers import format_identifier, normalize_username


@dataclass
class UserSummary:
    user_id: uuid.UUID
    display_name: str
    identifier: str
    # A conversa 1:1 com este utilizador, se já existir - deixa o cliente ligar
    # as mensagens guardadas (por conversa) à entrada certa da lista (por user).
    conversation_id: uuid.UUID | None = None


MAX_DISPLAY_NAME_LENGTH = 80


class DisplayNameError(Exception):
    pass


def clean_display_name(display_name: str) -> str:
    display_name = display_name.strip()
    if not display_name:
        raise DisplayNameError("O nome de exibição não pode ficar vazio")
    if len(display_name) > MAX_DISPLAY_NAME_LENGTH:
        raise DisplayNameError(
            f"O nome de exibição tem no máximo {MAX_DISPLAY_NAME_LENGTH} caracteres"
        )
    return display_name


def update_display_name(user_id: uuid.UUID, display_name: str) -> str:
    display_name = clean_display_name(display_name)
    User.update(display_name=display_name).where(User.id == user_id).execute()
    return display_name


def find_local_user_id(username: str) -> uuid.UUID | None:
    user = User.get_or_none(User.username == normalize_username(username), User.domain.is_null())
    return None if user is None else user.id


def local_profile(username: str) -> tuple[str, str] | None:
    user = User.get_or_none(User.username == normalize_username(username), User.domain.is_null())
    if user is None:
        return None
    return format_identifier(user.username, None), user.display_name


def summary_of(user: User, viewer_id: uuid.UUID) -> UserSummary:
    return UserSummary(
        user_id=user.id,
        display_name=user.display_name,
        identifier=format_identifier(user.username, user.domain),
        conversation_id=find_conversation(viewer_id, user.id),
    )


# Só no modo diretório: os utilizadores-sombra não são membros deste servidor.
def list_other_users(exclude_user_id: uuid.UUID) -> list[UserSummary]:
    users = (
        User.select()
        .where(User.id != exclude_user_id, User.domain.is_null())
        .order_by(User.created_at)
    )
    return [summary_of(user, exclude_user_id) for user in users]
