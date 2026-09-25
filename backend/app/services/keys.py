import uuid
from dataclasses import dataclass

from app.db import db
from app.models import Device, OneTimePrekey


class DeviceNotFoundError(Exception):
    pass


class DeviceTokenMismatchError(Exception):
    pass


def publish_keys(
    device_id: uuid.UUID,
    client_token: str,
    identity_key: bytes,
    signed_prekey: bytes,
    signed_prekey_signature: bytes,
    signed_prekey_id: int,
    one_time_prekeys: list[tuple[int, bytes]],
) -> None:
    device = Device.get_or_none(Device.id == device_id, Device.is_active == True)  # noqa: E712
    if device is None:
        raise DeviceNotFoundError
    if device.client_token != client_token:
        raise DeviceTokenMismatchError

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
