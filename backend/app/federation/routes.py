from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import SERVER_NAME
from app.federation.auth import federation_origin
from app.federation.discovery import PROTOCOL_VERSION, WELL_KNOWN_PATH
from app.federation.keys import KEY_ID, public_key_b64, signing_key

router = APIRouter()


class WellKnownResponse(BaseModel):
    server_name: str
    versions: list[str]
    verify_keys: dict[str, str]


class PingResponse(BaseModel):
    origin: str
    server_name: str


@router.get(WELL_KNOWN_PATH)
def well_known() -> WellKnownResponse:
    return WellKnownResponse(
        server_name=SERVER_NAME,
        versions=[PROTOCOL_VERSION],
        verify_keys={KEY_ID: public_key_b64(signing_key())},
    )


# Primeiro endpoint assinado: serve para testar a autenticação entre
# servidores e para diagnóstico (dev/federation-ping.sh).
@router.get("/_federation/v1/ping")
def ping(origin: Annotated[str, Depends(federation_origin)]) -> PingResponse:
    return PingResponse(origin=origin, server_name=SERVER_NAME)
