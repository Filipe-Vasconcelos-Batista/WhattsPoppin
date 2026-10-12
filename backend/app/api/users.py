from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentIdentity
from app.core import config
from app.db.sync import run_sync
from app.services.connections import connection_manager
from app.services.contacts import watcher_ids
from app.services.messaging import active_device_ids
from app.services.users import DisplayNameError, update_display_name

router = APIRouter(prefix="/users")


class UpdateDisplayNameRequest(BaseModel):
    display_name: str


class DisplayNameResponse(BaseModel):
    display_name: str


@router.patch("/me/display_name", response_model=DisplayNameResponse)
async def update_display_name_endpoint(
    request: UpdateDisplayNameRequest, identity: CurrentIdentity
) -> DisplayNameResponse:
    try:
        display_name = await run_sync(update_display_name, identity.user_id, request.display_name)
    except DisplayNameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payload: dict[str, object] = {
        "type": "user_updated",
        "user": {
            "user_id": str(identity.user_id),
            "display_name": display_name,
            "identifier": identity.identifier,
        },
    }
    if config.SERVER_MODE == config.SERVER_MODE_DIRECTORY:
        await connection_manager.broadcast(payload, exclude=identity.device_id)
    else:
        user_ids = [identity.user_id, *await run_sync(watcher_ids, identity.user_id)]
        for user_id in user_ids:
            for device_id in await run_sync(active_device_ids, user_id):
                if device_id != identity.device_id:
                    await connection_manager.send_to_device(device_id, payload)
    return DisplayNameResponse(display_name=display_name)
