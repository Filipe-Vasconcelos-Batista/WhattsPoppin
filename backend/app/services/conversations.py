import uuid

from app.models import Conversation, ConversationParticipant


def get_or_create_conversation(user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> uuid.UUID:
    """1:1 só - a conversa nem existe na BD até alguém tocar no contacto e
    abrir a conversa pela primeira vez."""
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
    if existing is not None:
        conversation_id: uuid.UUID = existing.conversation.id
        return conversation_id

    conversation = Conversation.create()
    ConversationParticipant.create(conversation=conversation, user=user_a_id)
    ConversationParticipant.create(conversation=conversation, user=user_b_id)
    return conversation.id
