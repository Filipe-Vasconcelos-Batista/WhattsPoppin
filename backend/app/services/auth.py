import secrets
import uuid
from dataclasses import dataclass

import bcrypt

from app.models import Device, User

MIN_PASSWORD_LENGTH = 12


class AuthError(Exception):
    pass


@dataclass
class Identity:
    token: str
    user_id: uuid.UUID
    device_id: uuid.UUID
    display_name: str
    is_new_user: bool


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def _create_device_for(user: User) -> tuple[str, Device]:
    token = secrets.token_hex(16)
    device = Device.create(user=user, client_token=token)
    return token, device


def register(username: str, password: str) -> Identity:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"A password tem de ter pelo menos {MIN_PASSWORD_LENGTH} caracteres")
    if User.get_or_none(User.username == username) is not None:
        raise AuthError("Esse nome de utilizador já existe")

    user = User.create(
        username=username,
        display_name=username,
        password_hash=_hash_password(password),
    )
    token, device = _create_device_for(user)
    return Identity(
        token=token,
        user_id=user.id,
        device_id=device.id,
        display_name=user.display_name,
        is_new_user=True,
    )


def login(username: str, password: str) -> Identity:
    user = User.get_or_none(User.username == username)
    if user is None or not _verify_password(password, user.password_hash):
        raise AuthError("Utilizador ou password incorretos")

    token, device = _create_device_for(user)
    return Identity(
        token=token,
        user_id=user.id,
        device_id=device.id,
        display_name=user.display_name,
        is_new_user=False,
    )


def resume_session(token: str) -> Identity | None:
    device = Device.get_or_none(Device.client_token == token)
    if device is None:
        return None

    user = device.user
    return Identity(
        token=token,
        user_id=user.id,
        device_id=device.id,
        display_name=user.display_name,
        is_new_user=False,
    )
