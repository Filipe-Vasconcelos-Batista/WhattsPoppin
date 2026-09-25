import uuid
from typing import Any

from fastapi.testclient import TestClient

from app.models import PendingMessage
from app.services import outbox
from tests.helpers import conversation, envelope, outgoing, register, wait_until


def _ws(session: dict[str, Any]) -> str:
    return f"/ws?device_id={session['device_id']}"


def _pending(session: dict[str, Any]) -> list[dict[str, Any]]:
    return [payload for _, payload in outbox.pending_for(uuid.UUID(session["device_id"]))]


def test_sender_gets_sent_with_its_client_message_id(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)
    client_message_id = str(uuid.uuid4())

    with ws_client.websocket_connect(_ws(alice)) as alice_ws:
        alice_ws.send_json(
            outgoing(
                conversation_id,
                envelope(bob["device_id"], 0),
                client_message_id=client_message_id,
            )
        )
        sent = alice_ws.receive_json()

    assert sent == {"type": "sent", "client_message_id": client_message_id}
    assert _pending(bob)[0]["client_message_id"] == client_message_id


def test_recipient_ack_sends_delivered_receipt_to_sender(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)
    client_message_id = str(uuid.uuid4())

    with (
        ws_client.websocket_connect(_ws(alice)) as alice_ws,
        ws_client.websocket_connect(_ws(bob)) as bob_ws,
    ):
        alice_ws.send_json(
            outgoing(
                conversation_id,
                envelope(bob["device_id"], 0),
                client_message_id=client_message_id,
            )
        )
        assert alice_ws.receive_json()["type"] == "sent"

        message = bob_ws.receive_json()
        assert message["client_message_id"] == client_message_id
        bob_ws.send_json({"type": "ack", "message_ids": [message["message_id"]]})

        receipt = alice_ws.receive_json()

    assert receipt["type"] == "receipt"
    assert receipt["status"] == "delivered"
    assert receipt["conversation_id"] == conversation_id
    assert receipt["client_message_ids"] == [client_message_id]
    assert "message_id" in receipt


def test_delivered_receipt_waits_in_queue_while_sender_is_offline(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)
    client_message_id = str(uuid.uuid4())

    with ws_client.websocket_connect(_ws(alice)) as alice_ws:
        alice_ws.send_json(
            outgoing(
                conversation_id,
                envelope(bob["device_id"], 0),
                client_message_id=client_message_id,
            )
        )
        assert alice_ws.receive_json()["type"] == "sent"

    with ws_client.websocket_connect(_ws(bob)) as bob_ws:
        message = bob_ws.receive_json()
        bob_ws.send_json({"type": "ack", "message_ids": [message["message_id"]]})
        wait_until(lambda: len(_pending(alice)) == 1)

    with ws_client.websocket_connect(_ws(alice)) as alice_ws:
        receipt = alice_ws.receive_json()

    assert receipt["status"] == "delivered"
    assert receipt["client_message_ids"] == [client_message_id]


def test_acking_a_receipt_does_not_generate_another_receipt(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)
    outbox.enqueue(
        uuid.UUID(alice["device_id"]),
        {
            "type": "receipt",
            "status": "delivered",
            "conversation_id": conversation_id,
            "client_message_ids": [str(uuid.uuid4())],
        },
    )
    rows_before = PendingMessage.select().count()

    with ws_client.websocket_connect(_ws(alice)) as alice_ws:
        receipt = alice_ws.receive_json()
        alice_ws.send_json({"type": "ack", "message_ids": [receipt["message_id"]]})
        wait_until(lambda: _pending(alice) == [])

    assert PendingMessage.select().count() == rows_before - 1
    assert _pending(bob) == []


def test_acking_an_old_row_without_client_message_id_does_not_break(
    ws_client: TestClient,
) -> None:
    # Linhas criadas pela fila offline antes dos recibos não têm
    # client_message_id - o ack tem de as apagar sem derrubar a ligação.
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)
    outbox.enqueue(
        uuid.UUID(bob["device_id"]),
        {
            "type": "message",
            "conversation_id": conversation_id,
            "sender_device_id": alice["device_id"],
            "header": {"dh": "ZA==", "pn": 0, "n": 0},
            "ciphertext": "antigo",
            "x3dh": None,
        },
    )
    client_message_id = str(uuid.uuid4())

    with (
        ws_client.websocket_connect(_ws(alice)) as alice_ws,
        ws_client.websocket_connect(_ws(bob)) as bob_ws,
    ):
        old = bob_ws.receive_json()
        bob_ws.send_json({"type": "ack", "message_ids": [old["message_id"]]})
        wait_until(lambda: _pending(bob) == [])

        # A ligação do Bob continua viva: recebe e confirma uma mensagem nova
        alice_ws.send_json(
            outgoing(
                conversation_id,
                envelope(bob["device_id"], 1),
                client_message_id=client_message_id,
            )
        )
        assert alice_ws.receive_json()["type"] == "sent"
        new = bob_ws.receive_json()
        bob_ws.send_json({"type": "ack", "message_ids": [new["message_id"]]})
        receipt = alice_ws.receive_json()

    assert receipt["status"] == "delivered"
    assert receipt["client_message_ids"] == [client_message_id]


def test_read_receipt_reaches_the_sender_device(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)
    client_message_id = str(uuid.uuid4())

    with (
        ws_client.websocket_connect(_ws(alice)) as alice_ws,
        ws_client.websocket_connect(_ws(bob)) as bob_ws,
    ):
        bob_ws.send_json(
            {
                "type": "read",
                "conversation_id": conversation_id,
                "receipts": [
                    {"device_id": alice["device_id"], "client_message_ids": [client_message_id]}
                ],
            }
        )
        receipt = alice_ws.receive_json()

    assert receipt["type"] == "receipt"
    assert receipt["status"] == "read"
    assert receipt["client_message_ids"] == [client_message_id]


def test_read_receipt_for_device_outside_the_conversation_is_dropped(
    ws_client: TestClient,
) -> None:
    alice = register()
    bob = register()
    outsider = register()
    conversation_id = conversation(alice, bob)

    with (
        ws_client.websocket_connect(_ws(alice)) as alice_ws,
        ws_client.websocket_connect(_ws(bob)) as bob_ws,
    ):
        # Primeiro um recibo para quem não está na conversa (descartado), a
        # seguir um legítimo - quando este chega, o anterior já foi tratado.
        bob_ws.send_json(
            {
                "type": "read",
                "conversation_id": conversation_id,
                "receipts": [
                    {"device_id": outsider["device_id"], "client_message_ids": [str(uuid.uuid4())]}
                ],
            }
        )
        bob_ws.send_json(
            {
                "type": "read",
                "conversation_id": conversation_id,
                "receipts": [
                    {"device_id": alice["device_id"], "client_message_ids": [str(uuid.uuid4())]}
                ],
            }
        )
        assert alice_ws.receive_json()["status"] == "read"

    assert _pending(outsider) == []


def test_message_without_client_message_id_is_ignored(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)
    client_message_id = str(uuid.uuid4())

    with (
        ws_client.websocket_connect(_ws(alice)) as alice_ws,
        ws_client.websocket_connect(_ws(bob)) as bob_ws,
    ):
        alice_ws.send_json(
            {"conversation_id": conversation_id, "envelopes": [envelope(bob["device_id"], 9)]}
        )
        alice_ws.send_json(
            outgoing(
                conversation_id,
                envelope(bob["device_id"], 0),
                client_message_id=client_message_id,
            )
        )
        received = bob_ws.receive_json()
        sent = alice_ws.receive_json()

    assert received["client_message_id"] == client_message_id
    assert received["header"]["n"] == 0
    assert sent["client_message_id"] == client_message_id
