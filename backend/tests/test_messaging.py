from fastapi.testclient import TestClient

from tests.helpers import (
    b64,
    client,
    conversation,
    envelope,
    login_new_device,
    publish_keys,
    register,
)


def test_recipient_devices_excludes_sender_and_devices_without_keys() -> None:
    alice = register()
    bob = register()
    publish_keys(alice)
    publish_keys(bob)
    bob_keyless_device = login_new_device(bob["username"])
    conversation_id = conversation(alice, bob)

    response = client.get(
        f"/conversations/{conversation_id}/devices", params={"device_id": alice["device_id"]}
    )

    assert response.status_code == 200
    device_ids = response.json()["device_ids"]
    assert device_ids == [bob["device_id"]]
    assert bob_keyless_device["device_id"] not in device_ids


def test_websocket_routes_each_envelope_only_to_its_device(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    bob_second = login_new_device(bob["username"])
    conversation_id = conversation(alice, bob)

    with (
        ws_client.websocket_connect(f"/ws?device_id={alice['device_id']}") as alice_ws,
        ws_client.websocket_connect(f"/ws?device_id={bob['device_id']}") as bob_ws,
        ws_client.websocket_connect(f"/ws?device_id={bob_second['device_id']}") as bob_second_ws,
    ):
        alice_ws.send_json(
            {
                "conversation_id": conversation_id,
                "envelopes": [
                    envelope(bob["device_id"], 0),
                    envelope(bob_second["device_id"], 1),
                ],
            }
        )

        to_bob = bob_ws.receive_json()
        to_bob_second = bob_second_ws.receive_json()

    assert to_bob["type"] == "message"
    assert to_bob["sender_device_id"] == alice["device_id"]
    assert to_bob["conversation_id"] == conversation_id
    assert to_bob["header"]["n"] == 0
    assert to_bob["ciphertext"] == b64(b"ciphertext-0")
    assert "text" not in to_bob
    assert to_bob_second["header"]["n"] == 1


def test_websocket_drops_envelopes_for_devices_outside_theconversation(
    ws_client: TestClient,
) -> None:
    alice = register()
    bob = register()
    outsider = register()
    alice_bob = conversation(alice, bob)
    alice_outsider = conversation(alice, outsider)

    with (
        ws_client.websocket_connect(f"/ws?device_id={alice['device_id']}") as alice_ws,
        ws_client.websocket_connect(f"/ws?device_id={outsider['device_id']}") as outsider_ws,
    ):
        # Envelope para o outsider numa conversa em que ele não está - tem de
        # ser descartado. A seguir, uma mensagem legítima para ele: tem de ser
        # essa a primeira coisa que recebe.
        alice_ws.send_json(
            {"conversation_id": alice_bob, "envelopes": [envelope(outsider["device_id"], 7)]}
        )
        alice_ws.send_json(
            {"conversation_id": alice_outsider, "envelopes": [envelope(outsider["device_id"], 0)]}
        )

        received = outsider_ws.receive_json()

    assert received["conversation_id"] == alice_outsider
    assert received["header"]["n"] == 0


def test_websocket_ignores_malformed_payloads(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)

    with (
        ws_client.websocket_connect(f"/ws?device_id={alice['device_id']}") as alice_ws,
        ws_client.websocket_connect(f"/ws?device_id={bob['device_id']}") as bob_ws,
    ):
        alice_ws.send_json({"conversation_id": conversation_id, "text": "texto simples antigo"})
        alice_ws.send_json(
            {"conversation_id": conversation_id, "envelopes": [envelope(bob["device_id"], 0)]}
        )

        received = bob_ws.receive_json()

    assert received["header"]["n"] == 0
