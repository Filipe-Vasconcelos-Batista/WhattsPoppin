import base64
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from app.db import db
from app.db.sync import run_sync
from app.federation.client import FederationNotFoundError, FederationRequestError, federation_json
from app.models import ConversationParticipant, Device, User
from app.services.contacts import are_contacts
from app.services.identifiers import format_identifier, is_local
from app.services.keys import DeviceKeys, PrekeyBundle

logger = logging.getLogger(__name__)

MAX_REMOTE_DEVICES = 50


class RemoteDeviceError(Exception):
    pass


class RemoteDeviceNotFoundError(RemoteDeviceError):
    pass


class IdentityKeyChangedError(RemoteDeviceError):
    pass


@dataclass
class ShadowDevice:
    device_id: uuid.UUID
    owner_id: uuid.UUID
    username: str
    domain: str
    identity_key: bytes

    @property
    def owner_identifier(self) -> str:
        return format_identifier(self.username, self.domain)


def _bytes(data: dict[str, Any], field: str) -> bytes:
    value = data.get(field)
    if not isinstance(value, str):
        raise RemoteDeviceError(f"{field} em falta")
    try:
        return base64.b64decode(value, validate=True)
    except ValueError as error:
        raise RemoteDeviceError(f"{field} não é base64") from error


def _int(data: dict[str, Any], field: str) -> int:
    value = data.get(field)
    # Em Python um bool também é int, e true não é um id.
    if not isinstance(value, int) or isinstance(value, bool):
        raise RemoteDeviceError(f"{field} não é um inteiro")
    return value


def _parse_device(data: Any) -> DeviceKeys:
    if not isinstance(data, dict):
        raise RemoteDeviceError("device que não é um objeto")
    try:
        device_id = uuid.UUID(str(data.get("device_id")))
    except ValueError as error:
        raise RemoteDeviceError("device_id inválido") from error
    return DeviceKeys(
        device_id=device_id,
        identity_key=_bytes(data, "identity_key"),
        signed_prekey=_bytes(data, "signed_prekey"),
        signed_prekey_signature=_bytes(data, "signed_prekey_signature"),
        signed_prekey_id=_int(data, "signed_prekey_id"),
    )


def _parse_devices(data: dict[str, Any], identifier: str) -> list[DeviceKeys]:
    if data.get("identifier") != identifier:
        raise RemoteDeviceError(f"respondeu por {data.get('identifier')!r}")
    devices = data.get("devices")
    if not isinstance(devices, list):
        raise RemoteDeviceError("devices em falta")
    if len(devices) > MAX_REMOTE_DEVICES:
        raise RemoteDeviceError(f"{len(devices)} devices, mais do que {MAX_REMOTE_DEVICES}")
    return [_parse_device(device) for device in devices]


def _parse_bundle(data: dict[str, Any], identifier: str) -> PrekeyBundle:
    if data.get("identifier") != identifier:
        raise RemoteDeviceError(f"respondeu por {data.get('identifier')!r}")
    one_time_prekey_id = None
    one_time_prekey = None
    if data.get("one_time_prekey") is not None or data.get("one_time_prekey_id") is not None:
        one_time_prekey_id = _int(data, "one_time_prekey_id")
        one_time_prekey = _bytes(data, "one_time_prekey")
    return PrekeyBundle(
        identity_key=_bytes(data, "identity_key"),
        signed_prekey=_bytes(data, "signed_prekey"),
        signed_prekey_signature=_bytes(data, "signed_prekey_signature"),
        signed_prekey_id=_int(data, "signed_prekey_id"),
        one_time_prekey_id=one_time_prekey_id,
        one_time_prekey=one_time_prekey,
    )


def _remote_owner(user_id: uuid.UUID) -> tuple[str, str] | None:
    user = User.get_or_none(User.id == user_id)
    if user is None or user.domain is None or is_local(user.domain):
        return None
    return user.username, user.domain


def remote_contacts_in_conversation(
    conversation_id: uuid.UUID, user_id: uuid.UUID
) -> list[uuid.UUID]:
    participants = (
        ConversationParticipant.select(ConversationParticipant, User)
        .join(User)
        .where(
            ConversationParticipant.conversation == conversation_id,
            ConversationParticipant.user != user_id,
        )
    )
    return [
        participant.user.id
        for participant in participants
        if not is_local(participant.user.domain) and are_contacts(user_id, participant.user.id)
    ]


def store_remote_devices(user_id: uuid.UUID, devices: list[DeviceKeys]) -> None:
    kept: list[uuid.UUID] = []
    with db.atomic():
        for remote in devices:
            Device.insert(
                id=remote.device_id,
                user=user_id,
                identity_key=remote.identity_key,
                signed_prekey=remote.signed_prekey,
                signed_prekey_signature=remote.signed_prekey_signature,
                signed_prekey_id=remote.signed_prekey_id,
            ).on_conflict_ignore().execute()
            device = (
                Device.select(Device, User).join(User).where(Device.id == remote.device_id).get()
            )

            if device.user.id != user_id:
                logger.warning(
                    "device %s já pertence a outro utilizador - ignorado", remote.device_id
                )
                continue
            kept.append(device.id)
            if device.identity_key is None or bytes(device.identity_key) != remote.identity_key:
                logger.warning("device %s mudou de identity_key - recusada", remote.device_id)
                continue
            Device.update(
                signed_prekey=remote.signed_prekey,
                signed_prekey_signature=remote.signed_prekey_signature,
                signed_prekey_id=remote.signed_prekey_id,
                is_active=True,
            ).where(Device.id == device.id).execute()

        Device.update(is_active=False).where(
            Device.user == user_id, Device.id.not_in(kept)
        ).execute()


async def sync_remote_devices(user_id: uuid.UUID) -> None:
    owner = await run_sync(_remote_owner, user_id)
    if owner is None:
        return
    username, domain = owner
    identifier = format_identifier(username, domain)
    try:
        data = await federation_json(domain, "GET", f"/_federation/v1/users/{username}/devices")
        devices = _parse_devices(data, identifier)
    except FederationNotFoundError:
        devices = []
    except (FederationRequestError, RemoteDeviceError) as error:
        logger.warning("devices de %s recusados: %s", identifier, error)
        raise RemoteDeviceError(str(error)) from error
    await run_sync(store_remote_devices, user_id, devices)


def shadow_device(device_id: uuid.UUID) -> ShadowDevice | None:
    device = (
        Device.select(Device, User)
        .join(User)
        .where(Device.id == device_id, Device.is_active == True)  # noqa: E712
        .first()
    )
    if device is None or is_local(device.user.domain) or device.identity_key is None:
        return None
    return ShadowDevice(
        device_id=device.id,
        owner_id=device.user.id,
        username=device.user.username,
        domain=device.user.domain,
        identity_key=bytes(device.identity_key),
    )


def _deactivate(device_id: uuid.UUID) -> None:
    Device.update(is_active=False).where(Device.id == device_id).execute()


async def fetch_remote_bundle(shadow: ShadowDevice) -> PrekeyBundle:
    identifier = shadow.owner_identifier
    try:
        data = await federation_json(
            shadow.domain, "POST", f"/_federation/v1/devices/{shadow.device_id}/prekey-bundle"
        )
        bundle = _parse_bundle(data, identifier)
    except FederationNotFoundError as error:
        await run_sync(_deactivate, shadow.device_id)
        raise RemoteDeviceNotFoundError(str(error)) from error
    except (FederationRequestError, RemoteDeviceError) as error:
        logger.warning(
            "bundle do device %s de %s recusado: %s", shadow.device_id, identifier, error
        )
        raise RemoteDeviceError(str(error)) from error

    if bundle.identity_key != shadow.identity_key:
        logger.warning(
            "bundle do device %s de %s com outra identity_key - recusado",
            shadow.device_id,
            identifier,
        )
        raise IdentityKeyChangedError
    return bundle
