import hashlib
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api import ws
from app.models import Device
from tests.helpers import (
    auth_headers,
    client,
    connect,
    conversation,
    envelope,
    outgoing,
    register,
)

INVALID = {"Authorization": "Bearer not-a-real-token"}


def _protected_requests(session: dict[str, Any]) -> list[tuple[str, str, dict[str, Any] | None]]:
    device_id = session["device_id"]
    return [
        ("POST", "/conversations/with", {"other_user_id": session["user_id"]}),
        ("GET", f"/conversations/{uuid.uuid4()}/devices", None),
        ("POST", f"/devices/{device_id}/keys", {}),
        ("GET", f"/devices/{device_id}/prekey-bundle", None),
        ("PATCH", "/users/me/display_name", {"display_name": "Alguém"}),
    ]


@pytest.mark.parametrize("headers", [{}, INVALID, {"Authorization": "Token abc"}])
def test_rest_endpoints_require_a_valid_session(headers: dict[str, str]) -> None:
    alice = register()
    for method, path, body in _protected_requests(alice):
        response = client.request(method, path, headers=headers, json=body)
        assert response.status_code == 401, (method, path)


def test_session_with_invalid_token_returns_null() -> None:
    response = client.post("/auth/session", headers=INVALID)

    assert response.status_code == 200
    assert response.json() is None


def test_token_is_stored_only_as_hash() -> None:
    alice = register()

    device = Device.get_by_id(alice["device_id"])

    assert device.token_hash == hashlib.sha256(alice["token"].encode()).hexdigest()
    assert device.token_hash != alice["token"]


def test_inactive_device_cannot_resume_session() -> None:
    alice = register()
    Device.update(is_active=False).where(Device.id == alice["device_id"]).execute()

    assert client.post("/auth/session", headers=auth_headers(alice)).json() is None
    response = client.patch(
        "/users/me/display_name", headers=auth_headers(alice), json={"display_name": "Alguém"}
    )
    assert response.status_code == 401


def test_recipient_devices_of_a_foreign_conversation_is_not_found() -> None:
    alice = register()
    bob = register()
    mallory = register()
    conversation_id = conversation(alice, bob)

    response = client.get(
        f"/conversations/{conversation_id}/devices", headers=auth_headers(mallory)
    )

    assert response.status_code == 404


def test_conversation_with_unknown_user_is_not_found() -> None:
    alice = register()

    response = client.post(
        "/conversations/with",
        headers=auth_headers(alice),
        json={"other_user_id": str(uuid.uuid4())},
    )

    assert response.status_code == 404


def _assert_closed_unauthorized(websocket: Any) -> None:
    with pytest.raises(WebSocketDisconnect) as closed:
        websocket.receive_json()
    assert closed.value.code == ws.CLOSE_UNAUTHORIZED


def test_websocket_with_invalid_token_is_closed(ws_client: TestClient) -> None:
    with ws_client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "auth", "token": "not-a-real-token"})
        _assert_closed_unauthorized(websocket)


def test_websocket_that_does_not_authenticate_first_is_closed(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)

    with ws_client.websocket_connect("/ws") as websocket:
        websocket.send_json(outgoing(conversation_id, envelope(bob["device_id"], 0)))
        _assert_closed_unauthorized(websocket)


def test_websocket_without_auth_in_time_is_closed(
    ws_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ws, "AUTH_TIMEOUT_SECONDS", 0.1)

    with ws_client.websocket_connect("/ws") as websocket:
        _assert_closed_unauthorized(websocket)


def test_outsider_cannot_message_type_or_send_receipts_in_a_foreign_conversation(
    ws_client: TestClient,
) -> None:
    alice = register()
    bob = register()
    mallory = register()
    alice_bob = conversation(alice, bob)

    with (
        connect(ws_client, alice) as alice_ws,
        connect(ws_client, bob) as bob_ws,
        connect(ws_client, mallory) as mallory_ws,
    ):
        mallory_ws.send_json(outgoing(alice_bob, envelope(bob["device_id"], 7)))
        mallory_ws.send_json({"type": "typing", "conversation_id": alice_bob, "typing": True})
        mallory_ws.send_json(
            {
                "type": "read",
                "conversation_id": alice_bob,
                "receipts": [
                    {"device_id": alice["device_id"], "client_message_ids": [str(uuid.uuid4())]}
                ],
            }
        )
        # O "sent" só chega depois de a mensagem do Mallory ter sido tratada, e
        # o socket processa por ordem - quando chega, as três já foram.
        mallory_ws.send_json(outgoing(alice_bob, envelope(bob["device_id"], 8)))
        assert mallory_ws.receive_json()["type"] == "sent"
        assert mallory_ws.receive_json()["type"] == "sent"

        alice_ws.send_json(outgoing(alice_bob, envelope(bob["device_id"], 0)))
        to_alice = alice_ws.receive_json()
        to_bob = bob_ws.receive_json()

    assert to_alice["type"] == "sent"
    assert to_bob["type"] == "message"
    assert to_bob["sender_device_id"] == alice["device_id"]
