import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from app.db.sync import run_sync
from app.services.conversations import get_or_create_conversation

router = APIRouter()


class GetOrCreateConversationRequest(BaseModel):
    user_id: uuid.UUID
    other_user_id: uuid.UUID


class ConversationResponse(BaseModel):
    conversation_id: uuid.UUID


@router.post("/conversations/with", response_model=ConversationResponse)
async def with_user(request: GetOrCreateConversationRequest) -> ConversationResponse:
    conversation_id = await run_sync(
        get_or_create_conversation, request.user_id, request.other_user_id
    )
    return ConversationResponse(conversation_id=conversation_id)
