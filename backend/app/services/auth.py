import hashlib
import secrets
import uuid
from dataclasses import dataclass

import bcrypt

from app.models import Device, User
from app.services.identifiers import format_identifier, is_valid_username, normalize_username

MIN_PASSWORD_LENGTH = 12


class AuthError(Exception):
    pass


@dataclass
class Identity:
    token: str
    user_id: uuid.UUID
    device_id: uuid.UUID
    display_name: str
    identifier: str
    is_new_user: bool


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _create_device_for(user: User) -> tuple[str, Device]:
    token = secrets.token_hex(16)
    device = Device.create(user=user, token_hash=_hash_token(token))
    return token, device


def _local_user(username: str) -> User | None:
    return User.get_or_none(User.username == username, User.domain.is_null())


def register(username: str, password: str) -> Identity:
    username = normalize_username(username)
    if not is_valid_username(username):
        raise AuthError(
            "O nome de utilizador tem de ter 3 a 32 caracteres: letras, números, '.', '_' ou '-'"
        )
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"A password tem de ter pelo menos {MIN_PASSWORD_LENGTH} caracteres")
    if _local_user(username) is not None:
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
        identifier=format_identifier(user.username, user.domain),
        is_new_user=True,
    )


def login(username: str, password: str) -> Identity:
    user = _local_user(normalize_username(username))
    if user is None or not _verify_password(password, user.password_hash):
        raise AuthError("Utilizador ou password incorretos")

    token, device = _create_device_for(user)
    return Identity(
        token=token,
        user_id=user.id,
        device_id=device.id,
        display_name=user.display_name,
        identifier=format_identifier(user.username, user.domain),
        is_new_user=False,
    )


def resume_session(token: str) -> Identity | None:
    device = Device.get_or_none(
        Device.token_hash == _hash_token(token),
        Device.is_active == True,  # noqa: E712
    )
    if device is None:
        return None

    user = device.user
    return Identity(
        token=token,
        user_id=user.id,
        device_id=device.id,
        display_name=user.display_name,
        identifier=format_identifier(user.username, user.domain),
        is_new_user=False,
    )
