import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentIdentity
from app.core.config import SERVER_NAME
from app.db.sync import run_sync
from app.services.connections import connection_manager
from app.services.contacts import (
    ContactError,
    ContactNotFoundError,
    ContactSummary,
    accept_contact,
    contact_summary,
    list_contacts,
    remove_contact,
    request_contact,
)
from app.services.identifiers import IdentifierError, is_local, parse_identifier
from app.services.messaging import active_device_ids
from app.services.remote_users import (
    RemoteUserError,
    RemoteUserNotFoundError,
    fetch_remote_user,
)
from app.services.users import find_local_user_id

router = APIRouter(prefix="/contacts")


class AddContactRequest(BaseModel):
    identifier: str


class ContactResponse(BaseModel):
    user_id: uuid.UUID
    display_name: str
    identifier: str
    conversation_id: uuid.UUID | None = None
    status: str


def contact_response(summary: ContactSummary) -> ContactResponse:
    return ContactResponse(
        user_id=summary.user_id,
        display_name=summary.display_name,
        identifier=summary.identifier,
        conversation_id=summary.conversation_id,
        status=summary.status,
    )


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Utilizador não encontrado")


async def _resolve(identifier: str) -> uuid.UUID:
    identifier = identifier.strip().lower()
    if "@" not in identifier:
        identifier = f"{identifier}@{SERVER_NAME}"
    try:
        username, domain = parse_identifier(identifier)
    except IdentifierError as exc:
        raise HTTPException(status_code=400, detail="Identificador inválido") from exc

    if is_local(domain):
        user_id = await run_sync(find_local_user_id, username)
        if user_id is None:
            raise _not_found()
        return user_id

    try:
        return await fetch_remote_user(username, domain)
    except RemoteUserNotFoundError as exc:
        raise _not_found() from exc
    except RemoteUserError as exc:
        raise HTTPException(
            status_code=502, detail=f"Não foi possível contactar o servidor {domain}"
        ) from exc


async def _notify(user_a_id: uuid.UUID, user_b_id: uuid.UUID, exclude: uuid.UUID) -> None:
    for viewer_id, other_id in ((user_a_id, user_b_id), (user_b_id, user_a_id)):
        summary = await run_sync(contact_summary, viewer_id, other_id)
        payload: dict[str, object]
        if summary is None:
            payload = {"type": "contact_removed", "user_id": str(other_id)}
        else:
            payload = {
                "type": "contact_updated",
                "contact": contact_response(summary).model_dump(mode="json"),
            }
        for device_id in await run_sync(active_device_ids, viewer_id):
            if device_id != exclude:
                await connection_manager.send_to_device(device_id, payload)


async def _respond(identity_user_id: uuid.UUID, contact_id: uuid.UUID) -> ContactResponse:
    summary = await run_sync(contact_summary, identity_user_id, contact_id)
    if summary is None:
        raise _not_found()
    return contact_response(summary)


@router.get("", response_model=list[ContactResponse])
async def list_endpoint(identity: CurrentIdentity) -> list[ContactResponse]:
    contacts = await run_sync(list_contacts, identity.user_id)
    return [contact_response(contact) for contact in contacts]


@router.post("", response_model=ContactResponse)
async def add_endpoint(request: AddContactRequest, identity: CurrentIdentity) -> ContactResponse:
    contact_id = await _resolve(request.identifier)
    try:
        await run_sync(request_contact, identity.user_id, contact_id)
    except ContactError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ContactNotFoundError as exc:
        raise _not_found() from exc
    await _notify(identity.user_id, contact_id, identity.device_id)
    return await _respond(identity.user_id, contact_id)


@router.post("/{user_id}/accept", response_model=ContactResponse)
async def accept_endpoint(user_id: uuid.UUID, identity: CurrentIdentity) -> ContactResponse:
    try:
        await run_sync(accept_contact, identity.user_id, user_id)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Pedido não encontrado") from exc
    await _notify(identity.user_id, user_id, identity.device_id)
    return await _respond(identity.user_id, user_id)


@router.delete("/{user_id}", status_code=204)
async def remove_endpoint(user_id: uuid.UUID, identity: CurrentIdentity) -> None:
    try:
        await run_sync(remove_contact, identity.user_id, user_id)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Contacto não encontrado") from exc
    await _notify(identity.user_id, user_id, identity.device_id)
