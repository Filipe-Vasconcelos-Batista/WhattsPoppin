from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.sync import run_sync
from app.services.auth import resume_session
from app.services.connections import connection_manager
from app.services.users import DisplayNameError, update_display_name

router = APIRouter(prefix="/users")


class UpdateDisplayNameRequest(BaseModel):
    token: str
    display_name: str


class DisplayNameResponse(BaseModel):
    display_name: str


@router.patch("/me/display_name", response_model=DisplayNameResponse)
async def update_display_name_endpoint(request: UpdateDisplayNameRequest) -> DisplayNameResponse:
    identity = await run_sync(resume_session, request.token)
    if identity is None:
        raise HTTPException(status_code=401, detail="Sessão inválida")

    try:
        display_name = await run_sync(update_display_name, identity.user_id, request.display_name)
    except DisplayNameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Também chega aos outros devices do próprio utilizador, que assim
    # atualizam o "O meu perfil" sem refresh.
    await connection_manager.broadcast(
        {
            "type": "user_updated",
            "user": {"user_id": str(identity.user_id), "display_name": display_name},
        },
        exclude=identity.device_id,
    )
    return DisplayNameResponse(display_name=display_name)
