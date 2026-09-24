import uuid

from app.models import ConversationParticipant, Device


def find_recipient_device_ids(
    conversation_id: uuid.UUID, sender_device_id: uuid.UUID
) -> list[uuid.UUID]:
    sender_device = Device.get_by_id(sender_device_id)

    participants = ConversationParticipant.select().where(
        ConversationParticipant.conversation == conversation_id,
        ConversationParticipant.user != sender_device.user,
    )

    device_ids: list[uuid.UUID] = []
    for participant in participants:
        devices = Device.select().where(
            Device.user == participant.user,
            Device.is_active == True,  # noqa: E712
        )
        device_ids.extend(device.id for device in devices)
    return device_ids
