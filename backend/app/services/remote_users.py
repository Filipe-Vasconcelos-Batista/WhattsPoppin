import logging
import uuid

import peewee as pw

from app.db import db
from app.db.sync import run_sync
from app.federation.client import FederationNotFoundError, FederationRequestError, federation_json
from app.models import User
from app.services.identifiers import format_identifier
from app.services.users import DisplayNameError, clean_display_name

logger = logging.getLogger(__name__)


class RemoteUserError(Exception):
    pass


class RemoteUserNotFoundError(RemoteUserError):
    pass


async def fetch_remote_user(username: str, domain: str) -> uuid.UUID:
    identifier = format_identifier(username, domain)
    try:
        display_name = await _fetch_display_name(username, domain, identifier)
    except RemoteUserNotFoundError:
        raise
    except RemoteUserError as error:
        # O cliente só vê um 502 genérico; o motivo exato fica aqui.
        logger.warning("perfil de %s recusado: %s", identifier, error)
        raise
    return await run_sync(upsert_shadow_user, username, domain, display_name)


async def _fetch_display_name(username: str, domain: str, identifier: str) -> str:
    try:
        data = await federation_json(domain, "GET", f"/_federation/v1/users/{username}/profile")
    except FederationNotFoundError as error:
        raise RemoteUserNotFoundError(f"{identifier} não existe") from error
    except FederationRequestError as error:
        raise RemoteUserError(str(error)) from error

    if data.get("identifier") != identifier:
        raise RemoteUserError(f"{domain} respondeu por {data.get('identifier')!r}")
    display_name = data.get("display_name")
    if not isinstance(display_name, str):
        raise RemoteUserError(f"{domain} respondeu sem display_name")
    try:
        return clean_display_name(display_name)
    except DisplayNameError as error:
        raise RemoteUserError(f"{domain} respondeu com um display_name inválido") from error


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
