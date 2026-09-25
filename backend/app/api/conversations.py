import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from app.db.sync import run_sync
from app.services.conversations import get_or_create_conversation
from app.services.messaging import find_recipient_device_ids

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


class RecipientDevicesResponse(BaseModel):
    device_ids: list[uuid.UUID]


# Dispositivos para os quais quem envia tem de cifrar (um envelope por device) -
# só os activos e com chaves publicadas, excluindo os do próprio remetente.
@router.get("/conversations/{conversation_id}/devices", response_model=RecipientDevicesResponse)
async def recipient_devices(
    conversation_id: uuid.UUID, device_id: uuid.UUID
) -> RecipientDevicesResponse:
    device_ids = await run_sync(find_recipient_device_ids, conversation_id, device_id, True)
    return RecipientDevicesResponse(device_ids=device_ids)
