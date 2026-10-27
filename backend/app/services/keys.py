import uuid
from dataclasses import dataclass

from app.db import db
from app.models import Device, OneTimePrekey, User
from app.services.identifiers import format_identifier, normalize_username


class DeviceNotFoundError(Exception):
    pass


def publish_keys(
    device_id: uuid.UUID,
    identity_key: bytes,
    signed_prekey: bytes,
    signed_prekey_signature: bytes,
    signed_prekey_id: int,
    one_time_prekeys: list[tuple[int, bytes]],
) -> None:
    device = Device.get_or_none(Device.id == device_id, Device.is_active == True)  # noqa: E712
    if device is None:
        raise DeviceNotFoundError

    with db.atomic():
        device.identity_key = identity_key
        device.signed_prekey = signed_prekey
        device.signed_prekey_signature = signed_prekey_signature
        device.signed_prekey_id = signed_prekey_id
        device.save()

        OneTimePrekey.insert_many(
            [
                {"device": device.id, "key_id": key_id, "public_key": public_key}
                for key_id, public_key in one_time_prekeys
            ]
        ).execute()


@dataclass
class PrekeyBundle:
    identity_key: bytes | None
    signed_prekey: bytes | None
    signed_prekey_signature: bytes | None
    signed_prekey_id: int | None
    one_time_prekey_id: int | None
    one_time_prekey: bytes | None


def get_prekey_bundle(device_id: uuid.UUID) -> PrekeyBundle | None:
    device = Device.get_or_none(Device.id == device_id, Device.is_active == True)  # noqa: E712
    if device is None:
        return None

    one_time_prekey_id = None
    one_time_prekey = None
    with db.atomic():
        opk = (
            OneTimePrekey.select()
            .where(OneTimePrekey.device == device.id)
            .order_by(OneTimePrekey.key_id)
            .for_update(skip_locked=True)
            .first()
        )
        if opk is not None:
            one_time_prekey_id = opk.key_id
            one_time_prekey = opk.public_key
            opk.delete_instance()

    return PrekeyBundle(
        identity_key=device.identity_key,
        signed_prekey=device.signed_prekey,
        signed_prekey_signature=device.signed_prekey_signature,
        signed_prekey_id=device.signed_prekey_id,
        one_time_prekey_id=one_time_prekey_id,
        one_time_prekey=one_time_prekey,
    )


@dataclass
class DeviceKeys:
    device_id: uuid.UUID
    identity_key: bytes
    signed_prekey: bytes
    signed_prekey_signature: bytes
    signed_prekey_id: int


def local_devices_with_keys(username: str) -> tuple[str, list[DeviceKeys]] | None:
    user = User.get_or_none(User.username == normalize_username(username), User.domain.is_null())
    if user is None:
        return None
    devices = Device.select().where(
        Device.user == user.id,
        Device.is_active == True,  # noqa: E712
        Device.identity_key.is_null(False),
    )
    keys = [_keys_of(device) for device in devices]
    return format_identifier(user.username, None), [key for key in keys if key is not None]


def _keys_of(device: Device) -> DeviceKeys | None:
    if (
        device.identity_key is None
        or device.signed_prekey is None
        or device.signed_prekey_signature is None
        or device.signed_prekey_id is None
    ):
        return None
    return DeviceKeys(
        device_id=device.id,
        identity_key=bytes(device.identity_key),
        signed_prekey=bytes(device.signed_prekey),
        signed_prekey_signature=bytes(device.signed_prekey_signature),
        signed_prekey_id=device.signed_prekey_id,
    )


def local_device_owner(device_id: uuid.UUID) -> str | None:
    device = (
        Device.select(Device, User)
        .join(User)
        .where(
            Device.id == device_id,
            Device.is_active == True,  # noqa: E712
            Device.identity_key.is_null(False),
            User.domain.is_null(),
        )
        .first()
    )
    return None if device is None else format_identifier(device.user.username, None)
