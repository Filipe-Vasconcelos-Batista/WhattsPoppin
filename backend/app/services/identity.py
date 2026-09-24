import secrets
import uuid
from dataclasses import dataclass

from app.models import Device, User


@dataclass
class Identity:
    token: str
    user_id: uuid.UUID
    device_id: uuid.UUID
    display_name: str
    is_new_user: bool


def bootstrap_identity(token: str | None) -> Identity:
    device = Device.get_or_none(Device.client_token == token) if token else None

    if device is None:
        resolved_token = secrets.token_hex(16)
        display_name = f"Utilizador {User.select().count() + 1}"
        user = User.create(display_name=display_name, identity_public_key=b"")
        device = Device.create(user=user, client_token=resolved_token)
        is_new_user = True
    else:
        assert token is not None  # device só é encontrado se um token foi dado
        resolved_token = token
        user = device.user
        is_new_user = False

    return Identity(
        token=resolved_token,
        user_id=user.id,
        device_id=device.id,
        display_name=user.display_name,
        is_new_user=is_new_user,
    )
