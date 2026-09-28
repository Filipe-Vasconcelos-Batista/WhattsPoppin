import uuid

from app.models import Conversation, ConversationParticipant, User


class UserNotFoundError(Exception):
    pass


def is_participant(conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    return bool(
        ConversationParticipant.select()
        .where(
            ConversationParticipant.conversation == conversation_id,
            ConversationParticipant.user == user_id,
        )
        .exists()
    )


def find_conversation(user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> uuid.UUID | None:
    """A conversa 1:1 entre os dois, se já existir - nunca cria."""
    my_conversations = ConversationParticipant.select(ConversationParticipant.conversation).where(
        ConversationParticipant.user == user_a_id
    )
    existing = (
        ConversationParticipant.select()
        .where(
            ConversationParticipant.user == user_b_id,
            ConversationParticipant.conversation.in_(my_conversations),
        )
        .first()
    )
    if existing is None:
        return None
    conversation_id: uuid.UUID = existing.conversation_id
    return conversation_id


def get_or_create_conversation(user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> uuid.UUID:
    if User.get_or_none(User.id == user_b_id) is None:
        raise UserNotFoundError

    existing = find_conversation(user_a_id, user_b_id)
    if existing is not None:
        return existing

    conversation = Conversation.create()
    ConversationParticipant.create(conversation=conversation, user=user_a_id)
    ConversationParticipant.create(conversation=conversation, user=user_b_id)
    return conversation.id
