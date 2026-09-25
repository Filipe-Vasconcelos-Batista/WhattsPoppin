import uuid

from app.models import ConversationParticipant, Device


def find_recipient_device_ids(
    conversation_id: uuid.UUID,
    sender_device_id: uuid.UUID,
    with_keys_only: bool = False,
) -> list[uuid.UUID]:
    sender_device = Device.get_by_id(sender_device_id)

    participants = ConversationParticipant.select().where(
        ConversationParticipant.conversation == conversation_id,
        ConversationParticipant.user != sender_device.user,
    )

    device_ids: list[uuid.UUID] = []
    for participant in participants:
        query = Device.select().where(
            Device.user == participant.user,
            Device.is_active == True,  # noqa: E712
        )
        if with_keys_only:
            # Sem chaves publicadas não há como abrir sessão X3DH com o device
            query = query.where(Device.identity_key.is_null(False))
        device_ids.extend(device.id for device in query)
    return device_ids
