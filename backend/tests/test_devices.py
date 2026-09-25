import base64
import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register() -> tuple[str, str]:
    response = client.post(
        "/auth/register",
        json={"username": f"e2e-test-{uuid.uuid4().hex[:8]}", "password": "a-long-enough-password"},
    )
    assert response.status_code == 200
    body = response.json()
    return body["device_id"], body["token"]


def _keys_payload(client_token: str) -> dict:
    return {
        "client_token": client_token,
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
    device_id, token = _register()
    response = client.post(f"/devices/{device_id}/keys", json=_keys_payload(token))
    assert response.status_code == 204

    first = client.get(f"/devices/{device_id}/prekey-bundle")
    assert first.status_code == 200
    body = first.json()
    assert body["identity_key"] == base64.b64encode(b"i" * 32).decode()
    assert body["one_time_prekey_id"] in (1, 2)

    second = client.get(f"/devices/{device_id}/prekey-bundle")
    assert second.json()["one_time_prekey_id"] in (1, 2)
    assert second.json()["one_time_prekey_id"] != body["one_time_prekey_id"]

    third = client.get(f"/devices/{device_id}/prekey-bundle")
    assert third.json()["one_time_prekey_id"] is None
    assert third.json()["one_time_prekey"] is None


def test_publish_keys_wrong_token_is_forbidden() -> None:
    device_id, _ = _register()
    payload = _keys_payload("wrong-token")
    response = client.post(f"/devices/{device_id}/keys", json=payload)
    assert response.status_code == 403


def test_publish_keys_unknown_device_is_not_found() -> None:
    response = client.post(f"/devices/{uuid.uuid4()}/keys", json=_keys_payload("whatever"))
    assert response.status_code == 404


def test_prekey_bundle_unknown_device_is_not_found() -> None:
    response = client.get(f"/devices/{uuid.uuid4()}/prekey-bundle")
    assert response.status_code == 404
