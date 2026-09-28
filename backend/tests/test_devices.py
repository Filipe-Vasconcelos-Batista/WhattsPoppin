import base64
import uuid
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import auth_headers, register

client = TestClient(app)


def _keys_payload() -> dict[str, Any]:
    return {
        "identity_key": base64.b64encode(b"i" * 32).decode(),
        "signed_prekey": base64.b64encode(b"s" * 32).decode(),
        "signed_prekey_signature": base64.b64encode(b"g" * 64).decode(),
        "signed_prekey_id": 1,
        "one_time_prekeys": [
            {"key_id": 1, "public_key": base64.b64encode(b"o" * 32).decode()},
            {"key_id": 2, "public_key": base64.b64encode(b"p" * 32).decode()},
        ],
    }


def test_publish_and_fetch_prekey_bundle() -> None:
    bob = register()
    alice = register()
    response = client.post(
        f"/devices/{bob['device_id']}/keys", headers=auth_headers(bob), json=_keys_payload()
    )
    assert response.status_code == 204

    def fetch() -> dict[str, Any]:
        response = client.get(
            f"/devices/{bob['device_id']}/prekey-bundle", headers=auth_headers(alice)
        )
        assert response.status_code == 200
        body: dict[str, Any] = response.json()
        return body

    first = fetch()
    assert first["identity_key"] == base64.b64encode(b"i" * 32).decode()
    assert first["one_time_prekey_id"] in (1, 2)

    second = fetch()
    assert second["one_time_prekey_id"] in (1, 2)
    assert second["one_time_prekey_id"] != first["one_time_prekey_id"]

    third = fetch()
    assert third["one_time_prekey_id"] is None
    assert third["one_time_prekey"] is None


def test_publish_keys_for_another_device_is_forbidden() -> None:
    alice = register()
    mallory = register()
    response = client.post(
        f"/devices/{alice['device_id']}/keys", headers=auth_headers(mallory), json=_keys_payload()
    )
    assert response.status_code == 403


def test_prekey_bundle_unknown_device_is_not_found() -> None:
    alice = register()
    response = client.get(f"/devices/{uuid.uuid4()}/prekey-bundle", headers=auth_headers(alice))
    assert response.status_code == 404
