import uuid
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.federation import discovery
from app.models import Device
from app.models.contact import ACCEPTED, PENDING_OUTGOING
from app.services import outbox
from app.services.contacts import _set as set_contact
from app.services.conversations import get_or_create_conversation
from app.services.remote_users import upsert_shadow_user
from tests.helpers import (
    auth_headers,
    b64,
    client,
    connect,
    envelope,
    outgoing,
    publish_keys,
    register,
)
from tests.test_federation_auth import FakeRemote


@pytest.fixture
def remote(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeRemote]:
    fake = FakeRemote()
    monkeypatch.setattr(discovery, "transport", httpx2.MockTransport(fake.handle))
    yield fake


def _devices_uri(username: str) -> str:
    return f"/_federation/v1/users/{username}/devices"


def _bundle_uri(device_id: str) -> str:
    return f"/_federation/v1/devices/{device_id}/prekey-bundle"


def _publish_with_prekeys(session: dict[str, Any], *key_ids: int) -> None:
    response = client.post(
        f"/devices/{session['device_id']}/keys",
        headers=auth_headers(session),
        json={
            "identity_key": b64(b"i" * 32),
            "signed_prekey": b64(b"s" * 32),
            "signed_prekey_signature": b64(b"g" * 64),
            "signed_prekey_id": 1,
            "one_time_prekeys": [
                {"key_id": key_id, "public_key": b64(bytes([key_id]) * 32)} for key_id in key_ids
            ],
        },
    )
    assert response.status_code == 204


def test_devices_of_a_local_user_with_keys(remote: FakeRemote) -> None:
    alice = register()
    publish_keys(alice)
    uri = _devices_uri(alice["username"])

    response = client.get(uri, headers=remote.headers(uri=uri))

    assert response.status_code == 200
    assert response.json() == {
        "identifier": alice["identifier"],
        "devices": [
            {
                "device_id": alice["device_id"],
                "identity_key": b64(b"i" * 32),
                "signed_prekey": b64(b"s" * 32),
                "signed_prekey_signature": b64(b"g" * 64),
                "signed_prekey_id": 1,
            }
        ],
    }


def test_devices_without_keys_are_left_out(remote: FakeRemote) -> None:
    alice = register()
    uri = _devices_uri(alice["username"])

    response = client.get(uri, headers=remote.headers(uri=uri))

    assert response.status_code == 200
    assert response.json()["devices"] == []


def test_devices_of_unknown_and_shadow_users_are_not_found(remote: FakeRemote) -> None:
    username = f"sombra-{uuid.uuid4().hex[:8]}"
    upsert_shadow_user(username, "outro.test", "Sombra")

    for name in ("ninguem-aqui", username):
        uri = _devices_uri(name)
        assert client.get(uri, headers=remote.headers(uri=uri)).status_code == 404


def test_devices_need_a_signed_request() -> None:
    alice = register()

    assert client.get(_devices_uri(alice["username"])).status_code == 401


def test_bundle_of_a_local_device_spends_a_one_time_prekey(remote: FakeRemote) -> None:
    alice = register()
    _publish_with_prekeys(alice, 7, 8)
    uri = _bundle_uri(alice["device_id"])

    first = client.post(uri, headers=remote.headers(method="POST", uri=uri))
    second = client.post(uri, headers=remote.headers(method="POST", uri=uri))

    assert first.status_code == 200
    assert first.json() == {
        "identifier": alice["identifier"],
        "identity_key": b64(b"i" * 32),
        "signed_prekey": b64(b"s" * 32),
        "signed_prekey_signature": b64(b"g" * 64),
        "signed_prekey_id": 1,
        "one_time_prekey_id": 7,
        "one_time_prekey": b64(bytes([7]) * 32),
    }
    assert second.json()["one_time_prekey_id"] == 8


def test_bundle_of_a_device_without_keys_or_unknown_is_not_found(remote: FakeRemote) -> None:
    alice = register()

    for device_id in (alice["device_id"], str(uuid.uuid4())):
        uri = _bundle_uri(device_id)
        assert client.post(uri, headers=remote.headers(method="POST", uri=uri)).status_code == 404


def test_bundle_needs_a_signed_request() -> None:
    alice = register()
    publish_keys(alice)

    assert client.post(_bundle_uri(alice["device_id"])).status_code == 401


class OtherServer:
    """O servidor do bob: responde aos pedidos de devices e de bundles."""

    def __init__(self) -> None:
        self.domain = f"{uuid.uuid4().hex[:8]}.test"
        self.identifier = f"bob@{self.domain}"
        self.devices: list[dict[str, Any]] = []
        self.bundle: Any = None
        self.status = 200
        self.requests: list[httpx2.Request] = []

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if self.status != 200:
            return httpx2.Response(self.status)
        if request.url.path.endswith("/devices"):
            return httpx2.Response(
                200, json={"identifier": self.identifier, "devices": self.devices}
            )
        return httpx2.Response(200, json=self.bundle)


@pytest.fixture
def other_server(monkeypatch: pytest.MonkeyPatch) -> Iterator[OtherServer]:
    fake = OtherServer()
    monkeypatch.setattr(discovery, "transport", httpx2.MockTransport(fake.handle))
    yield fake


def _device(device_id: str, identity_key: bytes = b"I" * 32) -> dict[str, Any]:
    return {
        "device_id": device_id,
        "identity_key": b64(identity_key),
        "signed_prekey": b64(b"S" * 32),
        "signed_prekey_signature": b64(b"G" * 64),
        "signed_prekey_id": 3,
    }


def _bundle(server: OtherServer, identity_key: bytes = b"I" * 32) -> dict[str, Any]:
    return {
        "identifier": server.identifier,
        "identity_key": b64(identity_key),
        "signed_prekey": b64(b"S" * 32),
        "signed_prekey_signature": b64(b"G" * 64),
        "signed_prekey_id": 3,
        "one_time_prekey_id": 9,
        "one_time_prekey": b64(b"O" * 32),
    }


def _with_bob(server: OtherServer, status: str = ACCEPTED) -> tuple[dict[str, Any], str]:
    """A alice daqui, com o bob do outro servidor como contacto e uma conversa
    entre os dois. A aceitação só viaja na F6, por isso cria-se direto."""
    alice = register()
    publish_keys(alice)
    bob_id = upsert_shadow_user("bob", server.domain, "Bob")
    set_contact(uuid.UUID(alice["user_id"]), bob_id, status)
    conversation_id = get_or_create_conversation(uuid.UUID(alice["user_id"]), bob_id)
    return alice, str(conversation_id)


def _recipient_devices(session: dict[str, Any], conversation_id: str) -> list[str]:
    response = client.get(
        f"/conversations/{conversation_id}/devices", headers=auth_headers(session)
    )
    assert response.status_code == 200
    device_ids: list[str] = response.json()["device_ids"]
    return device_ids


def _get_bundle(session: dict[str, Any], device_id: str) -> Any:
    return client.get(f"/devices/{device_id}/prekey-bundle", headers=auth_headers(session))


def _shadow(device_id: str) -> Any:
    return Device.get_or_none(Device.id == device_id)


def test_remote_devices_are_fetched_and_kept_as_shadows(other_server: OtherServer) -> None:
    alice, conversation_id = _with_bob(other_server)
    bob_device = str(uuid.uuid4())
    other_server.devices = [_device(bob_device)]

    assert _recipient_devices(alice, conversation_id) == [bob_device]

    request = other_server.requests[0]
    assert request.method == "GET"
    assert str(request.url) == f"http://{other_server.domain}/_federation/v1/users/bob/devices"
    assert request.headers["authorization"].startswith("WP-Sig ")
    shadow = _shadow(bob_device)
    assert shadow.token_hash is None
    assert bytes(shadow.identity_key) == b"I" * 32


def test_devices_that_disappear_are_deactivated(other_server: OtherServer) -> None:
    alice, conversation_id = _with_bob(other_server)
    kept, gone = str(uuid.uuid4()), str(uuid.uuid4())
    other_server.devices = [_device(kept), _device(gone)]
    assert sorted(_recipient_devices(alice, conversation_id)) == sorted([kept, gone])

    other_server.devices = [_device(kept)]

    assert _recipient_devices(alice, conversation_id) == [kept]
    assert _shadow(gone).is_active is False


def test_a_device_id_that_belongs_to_someone_else_is_ignored(other_server: OtherServer) -> None:
    alice, conversation_id = _with_bob(other_server)
    carol = register()
    publish_keys(carol)
    other_server.devices = [_device(carol["device_id"])]

    assert _recipient_devices(alice, conversation_id) == []
    assert str(_shadow(carol["device_id"]).user_id) == carol["user_id"]


def test_a_changed_identity_key_is_not_accepted(other_server: OtherServer) -> None:
    alice, conversation_id = _with_bob(other_server)
    bob_device = str(uuid.uuid4())
    other_server.devices = [_device(bob_device)]
    _recipient_devices(alice, conversation_id)

    other_server.devices = [_device(bob_device, identity_key=b"X" * 32)]

    assert _recipient_devices(alice, conversation_id) == [bob_device]
    assert bytes(_shadow(bob_device).identity_key) == b"I" * 32


def test_too_many_devices_are_refused(other_server: OtherServer) -> None:
    alice, conversation_id = _with_bob(other_server)
    other_server.devices = [_device(str(uuid.uuid4())) for _ in range(51)]

    assert _recipient_devices(alice, conversation_id) == []


def test_server_down_uses_the_stored_devices(other_server: OtherServer) -> None:
    alice, conversation_id = _with_bob(other_server)
    bob_device = str(uuid.uuid4())
    other_server.devices = [_device(bob_device)]
    _recipient_devices(alice, conversation_id)

    other_server.status = 500

    assert _recipient_devices(alice, conversation_id) == [bob_device]


def test_no_proxy_without_an_accepted_contact(other_server: OtherServer) -> None:
    alice, conversation_id = _with_bob(other_server, status=PENDING_OUTGOING)

    assert _recipient_devices(alice, conversation_id) == []
    assert other_server.requests == []


def test_remote_bundle_comes_through_our_server(other_server: OtherServer) -> None:
    alice, conversation_id = _with_bob(other_server)
    bob_device = str(uuid.uuid4())
    other_server.devices = [_device(bob_device)]
    _recipient_devices(alice, conversation_id)
    other_server.bundle = _bundle(other_server)

    response = _get_bundle(alice, bob_device)

    assert response.status_code == 200
    assert response.json() == {
        "identity_key": b64(b"I" * 32),
        "signed_prekey": b64(b"S" * 32),
        "signed_prekey_signature": b64(b"G" * 64),
        "signed_prekey_id": 3,
        "one_time_prekey_id": 9,
        "one_time_prekey": b64(b"O" * 32),
    }
    request = other_server.requests[-1]
    assert request.method == "POST"
    assert request.url.path == _bundle_uri(bob_device)
    assert request.headers["authorization"].startswith("WP-Sig ")


def test_remote_bundle_with_another_identity_key_is_refused(other_server: OtherServer) -> None:
    alice, conversation_id = _with_bob(other_server)
    bob_device = str(uuid.uuid4())
    other_server.devices = [_device(bob_device)]
    _recipient_devices(alice, conversation_id)
    other_server.bundle = _bundle(other_server, identity_key=b"X" * 32)

    assert _get_bundle(alice, bob_device).status_code == 409


@pytest.mark.parametrize(
    "change",
    [
        {"identifier": "carol@outro.test"},
        {"identity_key": "isto não é base64"},
        {"signed_prekey_id": True},
        {"one_time_prekey": None},
    ],
)
def test_malformed_remote_bundles_are_a_bad_gateway(
    other_server: OtherServer, change: dict[str, Any]
) -> None:
    alice, conversation_id = _with_bob(other_server)
    bob_device = str(uuid.uuid4())
    other_server.devices = [_device(bob_device)]
    _recipient_devices(alice, conversation_id)
    other_server.bundle = {**_bundle(other_server), **change}

    assert _get_bundle(alice, bob_device).status_code == 502


def test_remote_bundle_not_found_deactivates_the_device(other_server: OtherServer) -> None:
    alice, conversation_id = _with_bob(other_server)
    bob_device = str(uuid.uuid4())
    other_server.devices = [_device(bob_device)]
    _recipient_devices(alice, conversation_id)
    other_server.status = 404

    assert _get_bundle(alice, bob_device).status_code == 404
    assert _shadow(bob_device).is_active is False


def test_no_remote_bundle_without_an_accepted_contact(other_server: OtherServer) -> None:
    alice, conversation_id = _with_bob(other_server)
    bob_device = str(uuid.uuid4())
    other_server.devices = [_device(bob_device)]
    _recipient_devices(alice, conversation_id)
    set_contact(uuid.UUID(alice["user_id"]), _shadow(bob_device).user_id, PENDING_OUTGOING)
    requests_before = len(other_server.requests)

    assert _get_bundle(alice, bob_device).status_code == 403
    assert len(other_server.requests) == requests_before


def test_envelopes_for_remote_devices_stay_out_of_the_local_queue(
    other_server: OtherServer, ws_client: TestClient
) -> None:
    alice, conversation_id = _with_bob(other_server)
    bob_device = str(uuid.uuid4())
    other_server.devices = [_device(bob_device)]
    _recipient_devices(alice, conversation_id)

    with connect(ws_client, alice) as alice_ws:
        message = outgoing(conversation_id, envelope(bob_device, 0))
        alice_ws.send_json(message)
        sent = alice_ws.receive_json()

    assert sent == {"type": "sent", "client_message_id": message["client_message_id"]}
    assert outbox.pending_for(uuid.UUID(bob_device)) == []
