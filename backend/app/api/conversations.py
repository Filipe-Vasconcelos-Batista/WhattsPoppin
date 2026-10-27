import contextlib
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentIdentity
from app.core import config
from app.db.sync import run_sync
from app.services.contacts import are_contacts
from app.services.conversations import (
    UserNotFoundError,
    get_or_create_conversation,
    is_participant,
)
from app.services.messaging import find_recipient_device_ids
from app.services.remote_devices import (
    RemoteDeviceError,
    remote_contacts_in_conversation,
    sync_remote_devices,
)

router = APIRouter()


class GetOrCreateConversationRequest(BaseModel):
    other_user_id: uuid.UUID


class ConversationResponse(BaseModel):
    conversation_id: uuid.UUID


@router.post("/conversations/with", response_model=ConversationResponse)
async def with_user(
    request: GetOrCreateConversationRequest, identity: CurrentIdentity
) -> ConversationResponse:
    if config.SERVER_MODE == config.SERVER_MODE_PRIVATE and not await run_sync(
        are_contacts, identity.user_id, request.other_user_id
    ):
        raise HTTPException(status_code=403, detail="Só podes conversar com contactos aceites")
    try:
        conversation_id = await run_sync(
            get_or_create_conversation, identity.user_id, request.other_user_id
        )
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado") from exc
    return ConversationResponse(conversation_id=conversation_id)


class RecipientDevicesResponse(BaseModel):
    device_ids: list[uuid.UUID]


@router.get("/conversations/{conversation_id}/devices", response_model=RecipientDevicesResponse)
async def recipient_devices(
    conversation_id: uuid.UUID, identity: CurrentIdentity
) -> RecipientDevicesResponse:
    if not await run_sync(is_participant, conversation_id, identity.user_id):
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    for user_id in await run_sync(
        remote_contacts_in_conversation, conversation_id, identity.user_id
    ):
        with contextlib.suppress(RemoteDeviceError):
            await sync_remote_devices(user_id)
    device_ids = await run_sync(
        find_recipient_device_ids, conversation_id, identity.device_id, True, True
    )
    return RecipientDevicesResponse(device_ids=device_ids)
