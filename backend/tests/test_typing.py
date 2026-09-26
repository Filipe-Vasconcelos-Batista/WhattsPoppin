import uuid
from typing import Any

from fastapi.testclient import TestClient

from app.services import outbox
from tests.helpers import conversation, envelope, outgoing, register, wait_until


def _ws(session: dict[str, Any]) -> str:
    return f"/ws?device_id={session['device_id']}"


def _typing(conversation_id: str, typing: bool = True) -> dict[str, Any]:
    return {"type": "typing", "conversation_id": conversation_id, "typing": typing}


def _pending(session: dict[str, Any]) -> list[dict[str, Any]]:
    return [payload for _, payload in outbox.pending_for(uuid.UUID(session["device_id"]))]


def test_typing_reaches_connected_recipient(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)

    with (
        ws_client.websocket_connect(_ws(alice)) as alice_ws,
        ws_client.websocket_connect(_ws(bob)) as bob_ws,
    ):
        alice_ws.send_json(_typing(conversation_id))
        started = bob_ws.receive_json()
        alice_ws.send_json(_typing(conversation_id, typing=False))
        stopped = bob_ws.receive_json()

    assert started == {
        "type": "typing",
        "conversation_id": conversation_id,
        "sender_user_id": alice["user_id"],
        "typing": True,
    }
    assert stopped["typing"] is False
    assert _pending(bob) == []


def test_typing_is_not_queued_for_offline_recipient(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    conversation_id = conversation(alice, bob)

    with ws_client.websocket_connect(_ws(alice)) as alice_ws:
        alice_ws.send_json(_typing(conversation_id))
        # Uma mensagem a seguir: quando ela estiver na fila, o typing (enviado
        # antes, no mesmo socket) já foi processado.
        alice_ws.send_json(outgoing(conversation_id, envelope(bob["device_id"], 0)))
        wait_until(lambda: len(_pending(bob)) == 1)

    assert [payload["type"] for payload in _pending(bob)] == ["message"]


def test_typing_only_reaches_the_conversation_participants(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    outsider = register()
    alice_bob = conversation(alice, bob)
    alice_outsider = conversation(alice, outsider)

    with (
        ws_client.websocket_connect(_ws(alice)) as alice_ws,
        ws_client.websocket_connect(_ws(outsider)) as outsider_ws,
    ):
        alice_ws.send_json(_typing(alice_bob))
        alice_ws.send_json(_typing(alice_outsider))
        received = outsider_ws.receive_json()

    assert received["conversation_id"] == alice_outsider
