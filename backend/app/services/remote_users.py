import uuid

import peewee as pw

from app.db import db
from app.db.sync import run_sync
from app.federation.client import FederationRequestError, federation_request
from app.models import User
from app.services.identifiers import format_identifier
from app.services.users import DisplayNameError, clean_display_name


class RemoteUserError(Exception):
    pass


class RemoteUserNotFoundError(RemoteUserError):
    pass


async def fetch_remote_user(username: str, domain: str) -> uuid.UUID:
    identifier = format_identifier(username, domain)
    try:
        response = await federation_request(
            domain, "GET", f"/_federation/v1/users/{username}/profile"
        )
    except FederationRequestError as error:
        raise RemoteUserError(str(error)) from error

    if response.status_code == 404:
        raise RemoteUserNotFoundError(f"{identifier} não existe")
    if response.status_code != 200:
        raise RemoteUserError(f"{domain} respondeu {response.status_code}")

    try:
        data = response.json()
    except ValueError as error:
        raise RemoteUserError(f"{domain} respondeu com algo que não é JSON") from error
    if not isinstance(data, dict):
        raise RemoteUserError(f"{domain} respondeu com algo que não é um objeto")

    if data.get("identifier") != identifier:
        raise RemoteUserError(f"{domain} respondeu por {data.get('identifier')!r}")
    display_name = data.get("display_name")
    if not isinstance(display_name, str):
        raise RemoteUserError(f"{domain} respondeu sem display_name")
    try:
        display_name = clean_display_name(display_name)
    except DisplayNameError as error:
        raise RemoteUserError(f"{domain} respondeu com um display_name inválido") from error

    return await run_sync(upsert_shadow_user, username, domain, display_name)


def upsert_shadow_user(username: str, domain: str, display_name: str) -> uuid.UUID:
    existing = User.get_or_none(User.username == username, User.domain == domain)
    if existing is not None:
        if existing.display_name != display_name:
            User.update(display_name=display_name).where(User.id == existing.id).execute()
        return existing.id

    try:
        with db.atomic():
            user = User.create(
                username=username, domain=domain, password_hash="", display_name=display_name
            )
    except pw.IntegrityError:
        user = User.get(User.username == username, User.domain == domain)
    return user.id
