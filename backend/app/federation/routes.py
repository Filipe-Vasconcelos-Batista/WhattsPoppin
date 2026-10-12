from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import SERVER_NAME
from app.db.sync import run_sync
from app.federation.auth import federation_origin
from app.federation.discovery import PROTOCOL_VERSION, WELL_KNOWN_PATH
from app.federation.keys import KEY_ID, public_key_b64, signing_key
from app.services.users import local_profile

router = APIRouter()


class WellKnownResponse(BaseModel):
    server_name: str
    versions: list[str]
    verify_keys: dict[str, str]


class PingResponse(BaseModel):
    origin: str
    server_name: str


class ProfileResponse(BaseModel):
    identifier: str
    display_name: str


@router.get(WELL_KNOWN_PATH)
def well_known() -> WellKnownResponse:
    return WellKnownResponse(
        server_name=SERVER_NAME,
        versions=[PROTOCOL_VERSION],
        verify_keys={KEY_ID: public_key_b64(signing_key())},
    )


@router.get("/_federation/v1/ping")
def ping(origin: Annotated[str, Depends(federation_origin)]) -> PingResponse:
    return PingResponse(origin=origin, server_name=SERVER_NAME)


@router.get("/_federation/v1/users/{username}/profile")
async def profile(
    username: str, _origin: Annotated[str, Depends(federation_origin)]
) -> ProfileResponse:
    found = await run_sync(local_profile, username)
    if found is None:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    identifier, display_name = found
    return ProfileResponse(identifier=identifier, display_name=display_name)
