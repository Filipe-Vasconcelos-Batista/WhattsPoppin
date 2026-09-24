import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from app.db.sync import run_sync
from app.services.connections import connection_manager
from app.services.identity import bootstrap_identity
from app.services.users import list_other_users

router = APIRouter()


class BootstrapRequest(BaseModel):
    token: str | None = None


class UserSummaryResponse(BaseModel):
    user_id: uuid.UUID
    display_name: str


class BootstrapResponse(BaseModel):
    token: str
    user_id: uuid.UUID
    device_id: uuid.UUID
    display_name: str
    other_users: list[UserSummaryResponse]


@router.post("/identity/bootstrap", response_model=BootstrapResponse)
async def bootstrap(request: BootstrapRequest) -> BootstrapResponse:
    identity = await run_sync(bootstrap_identity, request.token)
    other_users = await run_sync(list_other_users, identity.user_id)

    # avisa quem já está ligado de que há alguém novo, para a lista de
    # conversas deles atualizar sem precisarem de refresh
    if identity.is_new_user:
        await connection_manager.broadcast(
            {
                "type": "user_registered",
                "user": {"user_id": str(identity.user_id), "display_name": identity.display_name},
            },
            exclude=identity.device_id,
        )

    return BootstrapResponse(
        token=identity.token,
        user_id=identity.user_id,
        device_id=identity.device_id,
        display_name=identity.display_name,
        other_users=[
            UserSummaryResponse(user_id=user.user_id, display_name=user.display_name)
            for user in other_users
        ],
    )
