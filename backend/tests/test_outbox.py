import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.models import PendingMessage
from app.services import outbox
from tests.helpers import conversation, envelope, register, wait_until


def _payload(sender: dict[str, Any], conversation_id: str, n: int) -> dict[str, Any]:
    return {
        "type": "message",
        "conversation_id": conversation_id,
        "sender_device_id": sender["device_id"],
        "header": {"dh": "ZA==", "pn": 0, "n": n},
        "ciphertext": f"ciphertext-{n}",
        "x3dh": None,
    }


def _pending_ids(session: dict[str, Any]) -> list[uuid.UUID]:
    return [message_id for message_id, _ in outbox.pending_for(uuid.UUID(session["device_id"]))]


def test_offline_recipient_receives_message_on_connect(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)

    with ws_client.websocket_connect(f"/ws?device_id={alice['device_id']}") as alice_ws:
        alice_ws.send_json(
            {"conversation_id": conversation_id, "envelopes": [envelope(bob["device_id"], 0)]}
        )
        wait_until(lambda: len(_pending_ids(bob)) == 1)

    with ws_client.websocket_connect(f"/ws?device_id={bob['device_id']}") as bob_ws:
        received = bob_ws.receive_json()

    assert received["type"] == "message"
    assert received["sender_device_id"] == alice["device_id"]
    assert received["header"]["n"] == 0
    assert received["message_id"] == str(_pending_ids(bob)[0])


def test_ack_removes_the_message_from_the_queue(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)
    outbox.enqueue(uuid.UUID(bob["device_id"]), _payload(alice, conversation_id, 0))

    with ws_client.websocket_connect(f"/ws?device_id={bob['device_id']}") as bob_ws:
        received = bob_ws.receive_json()
        bob_ws.send_json({"type": "ack", "message_ids": [received["message_id"]]})
        wait_until(lambda: _pending_ids(bob) == [])


def test_message_without_ack_is_redelivered_on_reconnect(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)
    outbox.enqueue(uuid.UUID(bob["device_id"]), _payload(alice, conversation_id, 0))

    with ws_client.websocket_connect(f"/ws?device_id={bob['device_id']}") as bob_ws:
        first = bob_ws.receive_json()
    with ws_client.websocket_connect(f"/ws?device_id={bob['device_id']}") as bob_ws:
        second = bob_ws.receive_json()

    assert second["message_id"] == first["message_id"]


def test_pending_messages_are_delivered_in_order(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)
    for n in range(3):
        outbox.enqueue(uuid.UUID(bob["device_id"]), _payload(alice, conversation_id, n))

    with ws_client.websocket_connect(f"/ws?device_id={bob['device_id']}") as bob_ws:
        received = [bob_ws.receive_json()["header"]["n"] for _ in range(3)]

    assert received == [0, 1, 2]


def test_ack_from_another_device_does_not_delete(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    carol = register()
    bob_message_id = outbox.enqueue(
        uuid.UUID(bob["device_id"]), _payload(alice, conversation(alice, bob), 0)
    )
    outbox.enqueue(uuid.UUID(carol["device_id"]), _payload(alice, conversation(alice, carol), 0))

    with ws_client.websocket_connect(f"/ws?device_id={carol['device_id']}") as carol_ws:
        carol_message = carol_ws.receive_json()
        # O ack do Carol inclui o id da mensagem do Bob: só a dele pode sair
        carol_ws.send_json(
            {"type": "ack", "message_ids": [str(bob_message_id), carol_message["message_id"]]}
        )
        wait_until(lambda: _pending_ids(carol) == [])

    assert _pending_ids(bob) == [bob_message_id]


def test_live_delivery_stays_pending_until_ack(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)

    with (
        ws_client.websocket_connect(f"/ws?device_id={alice['device_id']}") as alice_ws,
        ws_client.websocket_connect(f"/ws?device_id={bob['device_id']}") as bob_ws,
    ):
        alice_ws.send_json(
            {"conversation_id": conversation_id, "envelopes": [envelope(bob["device_id"], 0)]}
        )
        received = bob_ws.receive_json()
        assert [str(message_id) for message_id in _pending_ids(bob)] == [received["message_id"]]

        bob_ws.send_json({"type": "ack", "message_ids": [received["message_id"]]})
        wait_until(lambda: _pending_ids(bob) == [])


def test_purge_expired_removes_only_old_messages() -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)
    bob_device = uuid.UUID(bob["device_id"])
    recent_id = outbox.enqueue(bob_device, _payload(alice, conversation_id, 1))
    old = PendingMessage.create(
        recipient_device=bob_device,
        payload="{}",
        created_at=datetime.now(UTC) - outbox.PENDING_TTL - timedelta(days=1),
    )

    outbox.purge_expired()

    remaining = _pending_ids(bob)
    assert old.id not in remaining
    assert recent_id in remaining
