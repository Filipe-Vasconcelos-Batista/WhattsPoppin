import base64
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.devices import PrekeyBundleResponse, bundle_response
from app.core.config import SERVER_NAME
from app.db.sync import run_sync
from app.federation.auth import federation_origin
from app.federation.discovery import PROTOCOL_VERSION, WELL_KNOWN_PATH
from app.federation.keys import KEY_ID, public_key_b64, signing_key
from app.services.keys import get_prekey_bundle, local_device_owner, local_devices_with_keys
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


class FederatedDevice(BaseModel):
    device_id: uuid.UUID
    identity_key: str  # base64
    signed_prekey: str  # base64
    signed_prekey_signature: str  # base64
    signed_prekey_id: int


class DevicesResponse(BaseModel):
    identifier: str
    devices: list[FederatedDevice]


class FederatedPrekeyBundleResponse(PrekeyBundleResponse):
    identifier: str


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


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


@router.get("/_federation/v1/users/{username}/devices")
async def devices(
    username: str, _origin: Annotated[str, Depends(federation_origin)]
) -> DevicesResponse:
    found = await run_sync(local_devices_with_keys, username)
    if found is None:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    identifier, keys = found
    return DevicesResponse(
        identifier=identifier,
        devices=[
            FederatedDevice(
                device_id=device.device_id,
                identity_key=_b64(device.identity_key),
                signed_prekey=_b64(device.signed_prekey),
                signed_prekey_signature=_b64(device.signed_prekey_signature),
                signed_prekey_id=device.signed_prekey_id,
            )
            for device in keys
        ],
    )


@router.post("/_federation/v1/devices/{device_id}/prekey-bundle")
async def prekey_bundle(
    device_id: uuid.UUID, _origin: Annotated[str, Depends(federation_origin)]
) -> FederatedPrekeyBundleResponse:
    not_found = HTTPException(status_code=404, detail="Device não encontrado")
    identifier = await run_sync(local_device_owner, device_id)
    if identifier is None:
        raise not_found
    bundle = await run_sync(get_prekey_bundle, device_id)
    if bundle is None:
        raise not_found
    return FederatedPrekeyBundleResponse(
        identifier=identifier, **bundle_response(bundle).model_dump()
    )
