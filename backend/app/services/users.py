import uuid
from dataclasses import dataclass

from app.models import User


@dataclass
class UserSummary:
    user_id: uuid.UUID
    display_name: str


def list_other_users(exclude_user_id: uuid.UUID) -> list[UserSummary]:
    users = User.select().where(User.id != exclude_user_id).order_by(User.created_at)
    return [UserSummary(user_id=user.id, display_name=user.display_name) for user in users]
