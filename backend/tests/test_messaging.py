import base64
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PASSWORD = "a-long-enough-password"


# Fora de um `with`, o TestClient abre cada WebSocket no seu próprio event
# loop, e uma mensagem enviada do handler de um socket para outro nunca
# acorda quem está à espera (bloqueia para sempre). Dentro do `with` todos
# partilham um só loop, como no uvicorn.
@pytest.fixture
def ws_client() -> Iterator[TestClient]:
    with TestClient(app) as shared:
        yield shared


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def _register() -> dict[str, Any]:
    username = f"msg-test-{uuid.uuid4().hex[:8]}"
    response = client.post("/auth/register", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    return {**response.json(), "username": username}


def _login_new_device(username: str) -> dict[str, Any]:
    response = client.post("/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    session: dict[str, Any] = response.json()
    return session


def _publish_keys(session: dict[str, Any]) -> None:
    response = client.post(
        f"/devices/{session['device_id']}/keys",
        json={
            "client_token": session["token"],
            "identity_key": _b64(b"i" * 32),
            "signed_prekey": _b64(b"s" * 32),
            "signed_prekey_signature": _b64(b"g" * 64),
            "signed_prekey_id": 1,
            "one_time_prekeys": [],
        },
    )
    assert response.status_code == 204


def _conversation(a: dict[str, Any], b: dict[str, Any]) -> str:
    response = client.post(
        "/conversations/with", json={"user_id": a["user_id"], "other_user_id": b["user_id"]}
    )
    assert response.status_code == 200
    conversation_id: str = response.json()["conversation_id"]
    return conversation_id


def _envelope(device_id: str, n: int) -> dict[str, Any]:
    return {
        "device_id": device_id,
        "header": {"dh": _b64(b"d" * 32), "pn": 0, "n": n},
        "ciphertext": _b64(f"ciphertext-{n}".encode()),
        "x3dh": None,
    }


def test_recipient_devices_excludes_sender_and_devices_without_keys() -> None:
    alice = _register()
    bob = _register()
    _publish_keys(alice)
    _publish_keys(bob)
    bob_keyless_device = _login_new_device(bob["username"])
    conversation_id = _conversation(alice, bob)

    response = client.get(
        f"/conversations/{conversation_id}/devices", params={"device_id": alice["device_id"]}
    )

    assert response.status_code == 200
    device_ids = response.json()["device_ids"]
    assert device_ids == [bob["device_id"]]
    assert bob_keyless_device["device_id"] not in device_ids


def test_websocket_routes_each_envelope_only_to_its_device(ws_client: TestClient) -> None:
    alice = _register()
    bob = _register()
    bob_second = _login_new_device(bob["username"])
    conversation_id = _conversation(alice, bob)

    with (
        ws_client.websocket_connect(f"/ws?device_id={alice['device_id']}") as alice_ws,
        ws_client.websocket_connect(f"/ws?device_id={bob['device_id']}") as bob_ws,
        ws_client.websocket_connect(f"/ws?device_id={bob_second['device_id']}") as bob_second_ws,
    ):
        alice_ws.send_json(
            {
                "conversation_id": conversation_id,
                "envelopes": [
                    _envelope(bob["device_id"], 0),
                    _envelope(bob_second["device_id"], 1),
                ],
            }
        )

        to_bob = bob_ws.receive_json()
        to_bob_second = bob_second_ws.receive_json()

    assert to_bob["type"] == "message"
    assert to_bob["sender_device_id"] == alice["device_id"]
    assert to_bob["conversation_id"] == conversation_id
    assert to_bob["header"]["n"] == 0
    assert to_bob["ciphertext"] == _b64(b"ciphertext-0")
    assert "text" not in to_bob
    assert to_bob_second["header"]["n"] == 1


def test_websocket_drops_envelopes_for_devices_outside_the_conversation(
    ws_client: TestClient,
) -> None:
    alice = _register()
    bob = _register()
    outsider = _register()
    alice_bob = _conversation(alice, bob)
    alice_outsider = _conversation(alice, outsider)

    with (
        ws_client.websocket_connect(f"/ws?device_id={alice['device_id']}") as alice_ws,
        ws_client.websocket_connect(f"/ws?device_id={outsider['device_id']}") as outsider_ws,
    ):
        # Envelope para o outsider numa conversa em que ele não está - tem de
        # ser descartado. A seguir, uma mensagem legítima para ele: tem de ser
        # essa a primeira coisa que recebe.
        alice_ws.send_json(
            {"conversation_id": alice_bob, "envelopes": [_envelope(outsider["device_id"], 7)]}
        )
        alice_ws.send_json(
            {"conversation_id": alice_outsider, "envelopes": [_envelope(outsider["device_id"], 0)]}
        )

        received = outsider_ws.receive_json()

    assert received["conversation_id"] == alice_outsider
    assert received["header"]["n"] == 0


def test_websocket_ignores_malformed_payloads(ws_client: TestClient) -> None:
    alice = _register()
    bob = _register()
    conversation_id = _conversation(alice, bob)

    with (
        ws_client.websocket_connect(f"/ws?device_id={alice['device_id']}") as alice_ws,
        ws_client.websocket_connect(f"/ws?device_id={bob['device_id']}") as bob_ws,
    ):
        alice_ws.send_json({"conversation_id": conversation_id, "text": "texto simples antigo"})
        alice_ws.send_json(
            {"conversation_id": conversation_id, "envelopes": [_envelope(bob["device_id"], 0)]}
        )

        received = bob_ws.receive_json()

    assert received["header"]["n"] == 0
