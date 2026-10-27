import uuid

from app.core import config
from app.models import ConversationParticipant, Device
from app.services.contacts import are_contacts
from app.services.conversations import is_participant
from app.services.identifiers import is_local


def user_id_of_device(device_id: uuid.UUID) -> uuid.UUID:
    user_id: uuid.UUID = Device.get_by_id(device_id).user.id
    return user_id


def active_device_ids(user_id: uuid.UUID) -> list[uuid.UUID]:
    query = Device.select(Device.id).where(
        Device.user == user_id,
        Device.is_active == True,  # noqa: E712
    )
    return [device.id for device in query]


def find_recipient_device_ids(
    conversation_id: uuid.UUID,
    sender_device_id: uuid.UUID,
    with_keys_only: bool = False,
    include_remote: bool = False,
) -> list[uuid.UUID]:
    sender_device = Device.get_by_id(sender_device_id)

    if not is_participant(conversation_id, sender_device.user.id):
        return []

    participants = ConversationParticipant.select().where(
        ConversationParticipant.conversation == conversation_id,
        ConversationParticipant.user != sender_device.user,
    )

    device_ids: list[uuid.UUID] = []
    for participant in participants:
        if not include_remote and not is_local(participant.user.domain):
            continue
        if config.SERVER_MODE == config.SERVER_MODE_PRIVATE and not are_contacts(
            sender_device.user.id, participant.user.id
        ):
            continue
        query = Device.select().where(
            Device.user == participant.user,
            Device.is_active == True,  # noqa: E712
        )
        if with_keys_only:
            query = query.where(Device.identity_key.is_null(False))
        device_ids.extend(device.id for device in query)
    return device_ids
