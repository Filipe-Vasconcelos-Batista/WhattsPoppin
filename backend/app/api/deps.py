from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.db.sync import run_sync
from app.services.auth import Identity, resume_session

BEARER_PREFIX = "Bearer "

AuthorizationHeader = Annotated[str | None, Header()]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Sessão inválida",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _bearer_token(authorization: str | None) -> str | None:
    if authorization is None or not authorization.startswith(BEARER_PREFIX):
        return None
    token = authorization[len(BEARER_PREFIX) :].strip()
    return token or None


# O user e o device de quem faz o pedido saem sempre daqui, nunca de ids que o
# cliente mande - os servidores federados vão confiar no que dissermos sobre
# quem enviou.
async def current_identity(authorization: AuthorizationHeader = None) -> Identity:
    token = _bearer_token(authorization)
    if token is None:
        raise _unauthorized()
    identity = await run_sync(resume_session, token)
    if identity is None:
        raise _unauthorized()
    return identity


async def optional_identity(authorization: AuthorizationHeader = None) -> Identity | None:
    token = _bearer_token(authorization)
    if token is None:
        return None
    return await run_sync(resume_session, token)


CurrentIdentity = Annotated[Identity, Depends(current_identity)]
OptionalIdentity = Annotated[Identity | None, Depends(optional_identity)]
