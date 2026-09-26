import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.sync import run_sync
from app.services.auth import AuthError, Identity, login, register, resume_session
from app.services.connections import connection_manager
from app.services.users import list_other_users

router = APIRouter(prefix="/auth")


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class SessionRequest(BaseModel):
    token: str


class UserSummaryResponse(BaseModel):
    user_id: uuid.UUID
    display_name: str
    conversation_id: uuid.UUID | None = None


class AuthResponse(BaseModel):
    token: str
    user_id: uuid.UUID
    device_id: uuid.UUID
    display_name: str
    other_users: list[UserSummaryResponse]


async def _finish(identity: Identity) -> AuthResponse:
    other_users = await run_sync(list_other_users, identity.user_id)

    # avisa quem já está ligado, para a lista de conversas deles atualizar
    # sem precisarem de refresh
    if identity.is_new_user:
        await connection_manager.broadcast(
            {
                "type": "user_registered",
                "user": {"user_id": str(identity.user_id), "display_name": identity.display_name},
            },
            exclude=identity.device_id,
        )

    return AuthResponse(
        token=identity.token,
        user_id=identity.user_id,
        device_id=identity.device_id,
        display_name=identity.display_name,
        other_users=[
            UserSummaryResponse(
                user_id=user.user_id,
                display_name=user.display_name,
                conversation_id=user.conversation_id,
            )
            for user in other_users
        ],
    )


@router.post("/register", response_model=AuthResponse)
async def register_endpoint(request: RegisterRequest) -> AuthResponse:
    try:
        identity = await run_sync(register, request.username, request.password)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await _finish(identity)


@router.post("/login", response_model=AuthResponse)
async def login_endpoint(request: LoginRequest) -> AuthResponse:
    try:
        identity = await run_sync(login, request.username, request.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return await _finish(identity)


@router.post("/session", response_model=AuthResponse | None)
async def session_endpoint(request: SessionRequest) -> AuthResponse | None:
    identity = await run_sync(resume_session, request.token)
    if identity is None:
        return None
    return await _finish(identity)
