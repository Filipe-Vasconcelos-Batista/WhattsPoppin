import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentIdentity
from app.db.sync import run_sync
from app.services.conversations import (
    UserNotFoundError,
    get_or_create_conversation,
    is_participant,
)
from app.services.messaging import find_recipient_device_ids

router = APIRouter()


class GetOrCreateConversationRequest(BaseModel):
    other_user_id: uuid.UUID


class ConversationResponse(BaseModel):
    conversation_id: uuid.UUID


@router.post("/conversations/with", response_model=ConversationResponse)
async def with_user(
    request: GetOrCreateConversationRequest, identity: CurrentIdentity
) -> ConversationResponse:
    try:
        conversation_id = await run_sync(
            get_or_create_conversation, identity.user_id, request.other_user_id
        )
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado") from exc
    return ConversationResponse(conversation_id=conversation_id)


class RecipientDevicesResponse(BaseModel):
    device_ids: list[uuid.UUID]


# Dispositivos para os quais quem envia tem de cifrar (um envelope por device) -
# só os activos e com chaves publicadas, excluindo os do próprio remetente.
@router.get("/conversations/{conversation_id}/devices", response_model=RecipientDevicesResponse)
async def recipient_devices(
    conversation_id: uuid.UUID, identity: CurrentIdentity
) -> RecipientDevicesResponse:
    # 404 e não 403: quem não está na conversa nem fica a saber que ela existe.
    if not await run_sync(is_participant, conversation_id, identity.user_id):
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    device_ids = await run_sync(
        find_recipient_device_ids, conversation_id, identity.device_id, True
    )
    return RecipientDevicesResponse(device_ids=device_ids)
