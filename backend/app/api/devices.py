import base64
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.sync import run_sync
from app.services.keys import (
    DeviceNotFoundError,
    DeviceTokenMismatchError,
    get_prekey_bundle,
    publish_keys,
)

router = APIRouter()


class OneTimePrekeyIn(BaseModel):
    key_id: int
    public_key: str  # base64


class PublishKeysRequest(BaseModel):
    client_token: str
    identity_key: str  # base64, chave pública Ed25519
    signed_prekey: str  # base64, chave pública X25519
    signed_prekey_signature: str  # base64, assinatura Ed25519 sobre signed_prekey
    signed_prekey_id: int
    one_time_prekeys: list[OneTimePrekeyIn]


class PrekeyBundleResponse(BaseModel):
    identity_key: str | None
    signed_prekey: str | None
    signed_prekey_signature: str | None
    signed_prekey_id: int | None
    one_time_prekey_id: int | None
    one_time_prekey: str | None


def _b64_or_none(data: bytes | None) -> str | None:
    return base64.b64encode(data).decode() if data is not None else None


@router.post("/devices/{device_id}/keys", status_code=204)
async def publish_keys_endpoint(device_id: uuid.UUID, request: PublishKeysRequest) -> None:
    try:
        await run_sync(
            publish_keys,
            device_id,
            request.client_token,
            base64.b64decode(request.identity_key),
            base64.b64decode(request.signed_prekey),
            base64.b64decode(request.signed_prekey_signature),
            request.signed_prekey_id,
            [(opk.key_id, base64.b64decode(opk.public_key)) for opk in request.one_time_prekeys],
        )
    except DeviceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Device não encontrado") from exc
    except DeviceTokenMismatchError as exc:
        raise HTTPException(status_code=403, detail="Token não corresponde a este device") from exc


@router.get("/devices/{device_id}/prekey-bundle", response_model=PrekeyBundleResponse)
async def prekey_bundle_endpoint(device_id: uuid.UUID) -> PrekeyBundleResponse:
    bundle = await run_sync(get_prekey_bundle, device_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Device não encontrado")
    return PrekeyBundleResponse(
        identity_key=_b64_or_none(bundle.identity_key),
        signed_prekey=_b64_or_none(bundle.signed_prekey),
        signed_prekey_signature=_b64_or_none(bundle.signed_prekey_signature),
        signed_prekey_id=bundle.signed_prekey_id,
        one_time_prekey_id=bundle.one_time_prekey_id,
        one_time_prekey=_b64_or_none(bundle.one_time_prekey),
    )
